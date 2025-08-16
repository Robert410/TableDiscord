import os
import json
import discord
from discord.ext import commands
from pathlib import Path

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
    
    # Calculate column widths
    all_rows = [[str(i+1)] + row for i, row in enumerate(rows)]
    col_widths = [
        max(len(str(item)) for item in column)
        for column in zip(["#"] + headers, *all_rows)
    ]
    
    # Add padding (2 spaces each side)
    col_widths = [w + 4 for w in col_widths]
    
    # Build top border
    top_border = TOP_LEFT + TOP_LEFT.join(HORIZONTAL * w for w in col_widths) + TOP_RIGHT
    
    # Build header row
    header_row = VERTICAL + VERTICAL.join(
        f" {header.center(w-2)} " for header, w in zip(headers, col_widths)
    ) + VERTICAL
    
    # Build separator
    separator = VERTICAL + CROSS.join(HORIZONTAL * w for w in col_widths) + VERTICAL
    
    # Build data rows
    data_rows = []
    for i, row in enumerate(rows, 1):
        row_cells = VERTICAL + VERTICAL.join(
            f" {cell.ljust(w-2)} " for cell, w in zip(row, col_widths)
        ) + VERTICAL
        data_rows.append(f"{i:>2} {row_cells}")
    
    # Build bottom border
    bottom_border = BOTTOM_LEFT + BOTTOM_LEFT.join(HORIZONTAL * w for w in col_widths) + BOTTOM_RIGHT
    
    # Combine all parts
    return f"```diff\n+ Table Display 📊\n{top_border}\n{header_row}\n{separator}\n" + "\n".join(data_rows) + f"\n{bottom_border}\n```"

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
    await ctx.send(f"📝 Added column: **{colname}**")

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