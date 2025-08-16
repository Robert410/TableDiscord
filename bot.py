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
TABLES_DIR = Path("/data/tables")

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
    
    # Include row numbers in first column
    all_data = [[str(i+1)] + row for i, row in enumerate(rows)]
    all_data.insert(0, ["#"] + headers)

    # Calculate column widths (max length per column)
    col_widths = [max(len(str(item)) for item in col) for col in zip(*all_data)]

    # Build header row
    header = " | ".join(str(headers[i]).center(col_widths[i+1]) for i in range(len(headers)))
    header = " ".rjust(col_widths[0]) + " | " + header

    # Separator
    separator = "-+-".join("-" * w for w in col_widths)

    # Build data rows
    data_rows = []
    for i, row in enumerate(rows, 1):
        row_str = str(i).rjust(col_widths[0]) + " | "
        row_str += " | ".join(str(cell).ljust(col_widths[j+1]) for j, cell in enumerate(row))
        data_rows.append(row_str)

    # Combine all
    return (
        "```text\n"
        f"{header}\n"
        f"{separator}\n"
        + "\n".join(data_rows) +
        "\n```"
    )
# --- COMMANDS ---
@bot.command()
async def createtable(ctx):
    ensure_tables_dir()
    save_table(ctx.guild.id, {"headers": [], "rows": []})
    await ctx.send("✅ New table created for this server!")
    
@bot.command()
async def listfiles(ctx):
    """List all table JSON files in the tables directory"""
    ensure_tables_dir()
    files = list(TABLES_DIR.glob("*.json"))

    if not files:
        await ctx.send("📂 No tables found.")
        return

    file_list = "\n".join(f"- {f.name}" for f in files)
    await ctx.send(f"📂 Files in `tables/`:\n```\n{file_list}\n```")
    
@bot.command()
async def showfile(ctx, filename: str):
    """Show the raw JSON of a specific table file"""
    ensure_tables_dir()
    file_path = TABLES_DIR / filename

    if not file_path.exists():
        await ctx.send(f"⚠️ File `{filename}` not found.")
        return

    with open(file_path, "r") as f:
        content = f.read()

    # Discord message size limit safety (2000 chars)
    if len(content) > 1900:
        await ctx.send(f"⚠️ File `{filename}` is too large to display.")
    else:
        await ctx.send(f"📝 Contents of `{filename}`:\n```json\n{content}\n```")

@bot.command()
async def editcol(ctx, col_index: int, new_name: str):
    table = load_table(ctx.guild.id)

    if col_index < 1 or col_index > len(table["headers"]):
        await ctx.send(f"⚠️ Invalid column index! (1-{len(table['headers'])})")
        return

    old_name = table["headers"][col_index - 1]
    table["headers"][col_index - 1] = new_name
    save_table(ctx.guild.id, table)

    await ctx.send(f"✏️ Renamed column **{old_name}** → **{new_name}**")
    
@bot.command()
async def addcol(ctx, colname: str):
    table = load_table(ctx.guild.id)

    # Add column header
    table["headers"].append(colname)

    # Add null values for existing rows
    for row in table["rows"]:
        row.append("null")

    save_table(ctx.guild.id, table)
    await safe_send(ctx, f"📝 Added column: **{colname}** (default = null)")

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