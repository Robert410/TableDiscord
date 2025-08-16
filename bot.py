import os
import json
import discord
from discord.ext import commands
from pathlib import Path
from discord.ext import commands
import asyncio
from discord.errors import DiscordServerError

async def safe_send(ctx, message, max_retries=3):
    """Helper function to retry failed messages"""
    for attempt in range(max_retries):
        try:
            return await ctx.send(message)
        except DiscordServerError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1 + attempt)  # Exponential backoff

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- TABLE STORAGE ---
TABLES_DIR = Path("tables")

def ensure_tables_dir():
    """Create tables directory if it doesn't exist"""
    TABLES_DIR.mkdir(exist_ok=True)

def get_table_path(guild_id):
    """Get file path for a guild's table"""
    return TABLES_DIR / f"{guild_id}.json"

def load_table(guild_id):
    """Load table from file or return empty table"""
    file_path = get_table_path(guild_id)
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {"headers": [], "rows": []}

def save_table(guild_id, table):
    """Save table to file"""
    with open(get_table_path(guild_id), 'w') as f:
        json.dump(table, f)

# --- PRETTY TABLE FORMATTING ---
def format_table(headers, rows):
    if not headers:
        return "```\nNo table defined yet. Use !createtable first.\n```"
    
    # Box-drawing characters
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    HORIZONTAL = "─"
    VERTICAL = "│"
    CROSS = "┼"
    
    # Calculate column widths (including row numbers)
    all_data = [[str(i+1)] + row for i, row in enumerate(rows)]
    all_data.insert(0, ["#"] + headers)  # Add headers for width calculation
    
    # Get max width for each column (including padding)
    col_widths = [
        max(len(str(item)) + 4 for item in column)  # 2 spaces padding on each side
        for column in zip(*all_data)
    ]
    
    # Adjust row number column to be smaller
    col_widths[0] = max(4, col_widths[0])  # Minimum width of 4 for row numbers
    
    # Build top border
    top_border = TOP_LEFT + HORIZONTAL * (col_widths[0] + 1)  # +1 for space after number
    top_border += TOP_LEFT.join(HORIZONTAL * (w) for w in col_widths[1:]) + TOP_RIGHT
    
    # Build header row
    header_cells = [VERTICAL + f" {headers[i].center(col_widths[i+1]-2)} " for i in range(len(headers))]
    header_row = " " * (col_widths[0] + 1) + VERTICAL.join(header_cells) + VERTICAL
    
    # Build separator
    separator = " " * (col_widths[0] + 1) + VERTICAL
    separator += CROSS.join(HORIZONTAL * w for w in col_widths[1:]) + VERTICAL
    
    # Build data rows
    data_rows = []
    for i, row in enumerate(rows, 1):
        # Row number (right-aligned)
        row_str = f"{i:>{col_widths[0]-1}} "  # -1 to account for space
        
        # Cells
        row_str += VERTICAL
        row_str += VERTICAL.join(
            f" {str(cell).ljust(col_widths[j+1]-2)} " 
            for j, cell in enumerate(row)
        )
        row_str += VERTICAL
        
        data_rows.append(row_str)
    
    # Build bottom border
    bottom_border = BOTTOM_LEFT + HORIZONTAL * (col_widths[0] + 1)
    bottom_border += BOTTOM_LEFT.join(HORIZONTAL * w for w in col_widths[1:]) + BOTTOM_RIGHT
    
    # Combine all parts
    return (
        "```diff\n"
        "+ Table Display 📊\n"
        f"{top_border}\n"
        f"{header_row}\n"
        f"{separator}\n"
        + "\n".join(data_rows) + "\n"
        f"{bottom_border}\n"
        "```"
    )
# --- COMMANDS ---
@bot.command()
async def createtable(ctx):
    ensure_tables_dir()
    save_table(ctx.guild.id, {"headers": [], "rows": []})
    await ctx.send("✅ New table created for this server!")

@bot.command()
async def addcol(ctx, colname: str):
    table = load_table(ctx.guild.id)
    table["headers"].append(colname)
    save_table(ctx.guild.id, table)
    await safe_send(ctx, f"📝 Added column: **{colname}**")

@bot.command()
async def addrow(ctx, *values):
    table = load_table(ctx.guild.id)
    
    if len(values) != len(table["headers"]):
        await ctx.send(f"⚠️ Expected {len(table['headers'])} values, got {len(values)}!")
        return
        
    table["rows"].append(list(values))
    save_table(ctx.guild.id, table)
    await ctx.send(f"➕ Added row #{len(table['rows'])}")

@bot.command()
async def editrow(ctx, row_number: int, *new_values):
    table = load_table(ctx.guild.id)
    
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send(f"⚠️ Invalid row number! (1-{len(table['rows'])})")
        return
    if len(new_values) != len(table["headers"]):
        await ctx.send(f"⚠️ Expected {len(table['headers'])} values, got {len(new_values)}!")
        return
        
    table["rows"][row_number - 1] = list(new_values)
    save_table(ctx.guild.id, table)
    await ctx.send(f"✏️ Edited row #{row_number}")

@bot.command()
async def deleterow(ctx, row_number: int):
    table = load_table(ctx.guild.id)
    
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send(f"⚠️ Invalid row number! (1-{len(table['rows'])})")
        return
        
    deleted = table["rows"].pop(row_number - 1)
    save_table(ctx.guild.id, table)
    await ctx.send(f"🗑️ Deleted row #{row_number}: {', '.join(deleted)}")

@bot.command()
async def showtable(ctx):
    table = load_table(ctx.guild.id)
    await ctx.send(format_table(table["headers"], table["rows"]))

# Run bot
if __name__ == "__main__":
    ensure_tables_dir()
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)