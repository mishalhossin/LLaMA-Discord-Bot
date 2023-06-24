import os
from hugchat import hugchat
from hugchat.login import Login
import discord
from discord.ext import commands
import dotenv
import asyncio
from flask_app import run_flask_in_thread

# Set up the Discord bot
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, heartbeat_timeout=60)

TOKEN = os.environ.get('DISCORD_TOKEN')
email = os.environ.get('EMAIL')
passwd = os.environ.get('PASSWORD')

sign = Login(email, passwd)
cookies = sign.login()
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

sign.saveCookies()
allow_dm = True
active_channels = set()

def split_response(response, max_length=1999):
    lines = response.splitlines()
    chunks = []
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n"
            current_chunk += line

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
id = chatbot.new_conversation()
async def generate_response(user_prompt):
    chatbot.change_conversation(id)
    response = await asyncio.to_thread(chatbot.chat, text=user_prompt, is_retry=True)
    try:
      return response
    except:
      return "Model is overloaded, please try again later."


@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name="/help"))
    print(f"{bot.user.name} has connected to Discord!")
    invite_link = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(administrator=True),
        scopes=("bot", "applications.commands")
    )
    print(f"Invite link: {invite_link}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.reference and message.reference.resolved.author != bot.user:
        return
    
    if message.channel.id in active_channels or (allow_dm and isinstance(message.channel, discord.DMChannel)):
      
        user_prompt = message.content
        async with message.channel.typing():
            response = await generate_response(user_prompt)
        for chunk in split_response(response):
          await message.reply(chunk.replace("@", "@\u200B"))


@bot.hybrid_command(name="toggledm", description="Toggle DM for chatting.")
async def toggledm(ctx):
    global allow_dm
    allow_dm = not allow_dm
    await ctx.send(f"DMs are now {'allowed' if allow_dm else 'disallowed'} for active channels.")
    
@bot.hybrid_command(name="togglechannel", description="Toggle active channels.")
async def toggleactive(ctx):
    channel_id = ctx.channel.id
    if channel_id in active_channels:
        active_channels.remove(channel_id)
        with open("channels.txt", "w") as f:
            for id in active_channels:
                f.write(str(id) + "\n")
        await ctx.send(
            f"{ctx.channel.mention} has been removed from the list of active channels."
        )
    else:
        active_channels.add(channel_id)
        with open("channels.txt", "a") as f:
            f.write(str(channel_id) + "\n")
        await ctx.send(
            f"{ctx.channel.mention} has been added to the list of active channels!")
        

# Read the active channels from channels.txt on startup
if os.path.exists("channels.txt"):
    with open("channels.txt", "r") as f:
        for line in f:
            channel_id = int(line.strip())
            active_channels.add(channel_id)



bot.remove_command("help")   
@bot.hybrid_command(name="help", description="Get all other commands!")
async def help(ctx):
    embed = discord.Embed(title="Bot Commands", color=0x00ff00)
    embed.add_field(name="/togglechannel", value="Add the channel you are currently in to the Active Channel List.", inline=False)   
    embed.add_field(name="/toggledm", value="Toggle if DM chatting should be active", inline=False)
    
    await ctx.send(embed=embed)
  
run_flask_in_thread()

bot.run(TOKEN)
