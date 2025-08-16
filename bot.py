import os
import discord
from discord.ext import commands
import asyncpg

intents = discord.Intents.default()
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
    output = "--------------------\n"
    output += "| " + " | ".join(headers) + " |\n"
    output += "--------------------\n"
    for i, row in enumerate(rows, start=1):
        output += f"{i}. " + " | ".join(row) + "\n"
    return f"```\n{output}\n```"


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
async def createtable(ctx):
    await save_table(ctx.guild.id, {"headers": [], "rows": []})
    await ctx.send("✅ Table created!")


@bot.command()
async def addcol(ctx, colname: str):
    table = await get_table(ctx.guild.id)
    table["headers"].append(colname)
    await save_table(ctx.guild.id, table)
    await ctx.send(f"📝 Added column: **{colname}**")


@bot.command()
async def addrow(ctx, *values):
    table = await get_table(ctx.guild.id)
    if len(values) != len(table["headers"]):
        await ctx.send("⚠️ Number of values must match number of columns!")
        return
    table["rows"].append(list(values))
    await save_table(ctx.guild.id, table)
    await ctx.send(f"➕ Added row #{len(table['rows'])}")


@bot.command()
async def showtable(ctx):
    table = await get_table(ctx.guild.id)
    if not table["headers"]:
        await ctx.send("⚠️ No table exists. Use !createtable first.")
        return
    await ctx.send(format_table(table["headers"], table["rows"]))


@bot.command()
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
async def deleterow(ctx, row_number: int):
    table = await get_table(ctx.guild.id)
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send("⚠️ Invalid row number!")
        return
    table["rows"].pop(row_number - 1)
    await save_table(ctx.guild.id, table)
    await ctx.send(f"🗑️ Row {row_number} deleted!")


bot.run(os.environ["DISCORD_TOKEN"])
