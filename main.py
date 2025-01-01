import discord
from discord import app_commands
from discord.ext import tasks
import os
from keep_alive import keep_alive
import psutil
import aiohttp
import traceback
import secrets

if os.path.isfile(".env"):
    from dotenv import load_dotenv
    load_dotenv(verbose=True)

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client=client)

# サーバーごとの設定を保存する辞書
guild_settings = {}

@tree.command(name="setup_auth", description="認証メッセージを指定のチャンネルに設置します")
@app_commands.describe(
    channel="認証メッセージを送信するチャンネルを指定してください",
    role="認証成功時に付与するロールを指定してください",
    log_channel="ログを送信するチャンネルを指定してください"
)
async def setup_auth(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    role: discord.Role, 
    log_channel: discord.TextChannel
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    # サーバーの設定を保存
    guild_id = interaction.guild.id
    guild_settings[guild_id] = {
        "channel": channel,
        "role": role,
        "log_channel": log_channel
    }

    await interaction.response.send_message("認証メッセージのセットアップが完了しました。", ephemeral=True)

def generate_secure_code(length):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

class AuthorizeView(discord.ui.View):
    def __init__(self, code, role, log_channel, timeout=300):
        super().__init__(timeout=timeout)
        self.code = code
        self.role = role
        self.log_channel = log_channel

    @discord.ui.button(emoji="✅", label="書き込んだ", style=discord.ButtonStyle.primary)
    async def writed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://viper.2ch.sc/news4vip/dat/1710319736.dat") as response:
                    data = await response.read()
                    encoding = chardet.detect(data)['encoding']
                    dat = data.decode(encoding)
                    if self.code in dat:
                        await interaction.user.add_roles(self.role)
                        await self.log_channel.send(f"{interaction.user.mention} の認証が完了しました。")
                        await interaction.followup.send("**認証が完了しました。**", ephemeral=True)
                    else:
                        await interaction.followup.send("認証に失敗しました。", ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="エラーが発生しました。",
                description=f"詳細: {e}",
                color=discord.Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def on_button_click(interaction: discord.Interaction):
    custom_id = interaction.data["custom_id"]
    if custom_id == "authorize":
        guild_id = interaction.guild.id
        if guild_id in guild_settings:
            role = guild_settings[guild_id]["role"]
            log_channel = guild_settings[guild_id]["log_channel"]
            
            if role not in interaction.user.roles:
                code = generate_secure_code(10)
                view = AuthorizeView(code, role, log_channel, timeout=300)
                embed = discord.Embed(
                    title="サーバーに参加するためには、認証が必要です",
                    description=f"以下の文字列を投稿してください。\n```\nDiscord認証コード: {code}\n```",
                    color=discord.Colour.purple()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="あなたは既に認証しています！",
                    color=discord.Colour.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ping", description="pingを計測します")
async def ping(interaction: discord.Interaction):
    ping = client.latency
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    embed = discord.Embed(
        title="Ping",
        description=f"Ping: {ping*1000:.2f}ms\nCPU: {cpu_percent}%\nMemory: {mem.percent}%",
        color=discord.Colour.gold()
    )
    embed.set_thumbnail(url=client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

keep_alive()
client.run(os.getenv("discord"))
