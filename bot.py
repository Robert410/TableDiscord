import os
import discord
from discord.ext import commands
import asyncpg
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATABASE_URL = os.environ["DATABASE_URL"]
conn: asyncpg.Connection = None  # global connection


@bot.event
async def on_ready():
    global conn
    conn = await asyncpg.connect(DATABASE_URL)
    # Create table if it doesn't exist
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            guild_id TEXT PRIMARY KEY,
            headers TEXT[],
            rows JSONB
        )
    """)
    print(f"Logged in as {bot.user}")


def format_table(headers, rows):
    # Define box-drawing characters and icons
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    HORIZONTAL = "─"
    VERTICAL = "│"
    CROSS = "┼"
    RIGHT_T = "├"
    LEFT_T = "┤"
    TOP_T = "┬"
    BOTTOM_T = "┴"
    
    # Calculate column widths
    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Add padding (2 spaces on each side)
    col_widths = [w + 4 for w in col_widths]
    
    # Build the top border
    top_border = TOP_LEFT + TOP_T.join(HORIZONTAL * w for w in col_widths) + TOP_RIGHT
    
    # Build header row
    header_row = VERTICAL + VERTICAL.join(
        f" {header.center(col_widths[i]-2)} " for i, header in enumerate(headers)
    ) + VERTICAL
    
    # Build separator
    separator = RIGHT_T + CROSS.join(HORIZONTAL * w for w in col_widths) + LEFT_T
    
    # Build data rows
    data_rows = []
    for i, row in enumerate(rows, 1):
        row_cells = VERTICAL + VERTICAL.join(
            f" {str(cell).ljust(col_widths[j]-2)} " for j, cell in enumerate(row)
        ) + VERTICAL
        row_number = f"📋 {i}".ljust(5)  # Row number with icon
        data_rows.append(f"{row_number}{row_cells}")
    
    # Build bottom border
    bottom_border = BOTTOM_LEFT + BOTTOM_T.join(HORIZONTAL * w for w in col_widths) + BOTTOM_RIGHT
    
    # Combine all parts
    table = [
        "```diff",
        "+ Table Display 📊",
        top_border,
        header_row,
        separator
    ]
    table.extend(data_rows)
    table.append(bottom_border)
    table.append("```")
    
    return "\n".join(table)


async def get_table(guild_id):
    row = await conn.fetchrow("SELECT headers, rows FROM tables WHERE guild_id=$1", str(guild_id))
    if row:
        return {"headers": row["headers"], "rows": row["rows"]}
    return {"headers": [], "rows": []}


async def save_table(guild_id, table):
    await conn.execute("""
        INSERT INTO tables(guild_id, headers, rows)
        VALUES($1, $2, $3)
        ON CONFLICT(guild_id)
        DO UPDATE SET headers=$2, rows=$3
    """, str(guild_id), table["headers"], table["rows"])


# COMMANDS

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.guild) 
async def createtable(ctx):
    await save_table(ctx.guild.id, {"headers": [], "rows": []})
    await ctx.send("✅ Table created!")


@bot.command()
@commands.cooldown(1, 2, commands.BucketType.guild) 
async def addcol(ctx, colname: str):
    table = await get_table(ctx.guild.id)
    table["headers"].append(colname)
    await save_table(ctx.guild.id, table)
    await ctx.send(f"📝 Added column: **{colname}**")


@bot.command()
@commands.cooldown(1, 2, commands.BucketType.guild) 
async def addrow(ctx, *values):
    table = await get_table(ctx.guild.id)
    if len(values) != len(table["headers"]):
        await ctx.send("⚠️ Number of values must match number of columns!")
        return
    table["rows"].append(list(values))
    await save_table(ctx.guild.id, table)
    await ctx.send(f"➕ Added row #{len(table['rows'])}")


@bot.command()
@commands.cooldown(1, 2, commands.BucketType.guild) 
async def showtable(ctx):
    table = await get_table(ctx.guild.id)
    if not table["headers"]:
        await ctx.send("⚠️ No table exists. Use !createtable first.")
        return
    await ctx.send(format_table(table["headers"], table["rows"]))


@bot.command()
@commands.cooldown(1, 2, commands.BucketType.guild) 
async def editrow(ctx, row_number: int, *values):
    table = await get_table(ctx.guild.id)
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send("⚠️ Invalid row number!")
        return
    if len(values) != len(table["headers"]):
        await ctx.send("⚠️ Number of values must match number of columns!")
        return
    table["rows"][row_number - 1] = list(values)
    await save_table(ctx.guild.id, table)
    await ctx.send(f"✏️ Row {row_number} updated!")


@bot.command()
@commands.cooldown(1, 2, commands.BucketType.guild) 
async def deleterow(ctx, row_number: int):
    table = await get_table(ctx.guild.id)
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send("⚠️ Invalid row number!")
        return
    table["rows"].pop(row_number - 1)
    await save_table(ctx.guild.id, table)
    await ctx.send(f"🗑️ Row {row_number} deleted!")


bot.run(os.environ["DISCORD_TOKEN"])
