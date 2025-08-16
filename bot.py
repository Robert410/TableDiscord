import os
import discord
from discord.ext import commands

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- TABLE DATA (stored in memory) ---
table = {"headers": [], "rows": []}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# --- COMMANDS ---
@bot.command()
async def createtable(ctx):
    global table
    table = {"headers": [], "rows": []}
    await ctx.send("✅ New table created!")

@bot.command()
async def addcol(ctx, colname: str):
    table["headers"].append(colname)
    await ctx.send(f"📝 Added column: **{colname}**")

@bot.command()
async def addrow(ctx, *values):
    if len(values) != len(table["headers"]):
        await ctx.send("⚠️ Number of values must match number of columns!")
        return
    table["rows"].append(list(values))
    await ctx.send(f"➕ Added row #{len(table['rows'])}")

@bot.command()
async def editrow(ctx, row_number: int, *new_values):
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send("⚠️ Invalid row number!")
        return
    if len(new_values) != len(table["headers"]):
        await ctx.send("⚠️ Number of values must match number of columns!")
        return
    table["rows"][row_number - 1] = list(new_values)
    await ctx.send(f"✏️ Edited row #{row_number}")

@bot.command()
async def deleterow(ctx, row_number: int):
    if row_number < 1 or row_number > len(table["rows"]):
        await ctx.send("⚠️ Invalid row number!")
        return
    deleted = table["rows"].pop(row_number - 1)
    await ctx.send(f"🗑️ Deleted row #{row_number}: {deleted}")

@bot.command()
async def showtable(ctx):
    if not table["headers"]:
        await ctx.send("⚠️ No table defined yet.")
        return

    # Calculate column widths
    headers = ["#"] + table["headers"]
    rows_with_numbers = [[str(i+1)] + row for i, row in enumerate(table["rows"])]
    all_data = [headers] + rows_with_numbers
    col_widths = [max(len(str(x)) for x in col) for col in zip(*all_data)]

    # Build header row
    header_row = "| " + " | ".join(f"{name:<{w}}" for name, w in zip(headers, col_widths)) + " |"
    separator = "-" * len(header_row)

    # Build rows
    rows = [
        "| " + " | ".join(f"{val:<{w}}" for val, w in zip(row, col_widths)) + " |"
        for row in rows_with_numbers
    ]

    output = "\n".join([separator, header_row, separator] + rows + [separator])
    await ctx.send(f"```\n{output}\n```")

# Run bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
