import discord
from discord import app_commands
from discord.ext import tasks
import os
from keep_alive import keep_alive
import psutil
import aiohttp
import random
import string
import chardet
import traceback

if os.path.isfile(".env"):
    from dotenv import load_dotenv
    load_dotenv(verbose=True)

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client=client)

@client.event
async def on_ready():
    await tree.sync()
    print("起動完了！")

# 認証メッセージを指定のチャンネルに設置するコマンド
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

    code = random_code(10)
    view = AuthorizeView(code, role, log_channel, timeout=300)

    embed = discord.Embed(
        title="サーバー認証",
        description=(
            f"以下のコードを [こちらのスレッド](https://viper.2ch.sc/test/read.cgi/news4vip/1717936187/) に投稿してください。\n\n"
            f"認証用コード:\n```\nDiscord支部の認証用文字列です: {code}\n```\n\n"
            "投稿後に「✅書き込んだ」を押してください。"
        ),
        color=discord.Color.blue()
    )

    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"{channel.mention} に認証メッセージを設置しました！ログは {log_channel.mention} に送信されます。", ephemeral=True)

def random_code(length):
    alphanumeric_chars = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_chars) for _ in range(length))

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
                async with session.get("https://viper.2ch.sc/news4vip/dat/1717936187.dat") as response:
                    data = await response.read()
                    encoding = chardet.detect(data)['encoding']
                    dat = data.decode(encoding)

                    if self.code in dat:
                        await interaction.user.add_roles(self.role)
                        await interaction.followup.send("**認証が完了しました。**", ephemeral=True)
                        if self.log_channel:
                            await self.log_channel.send(f"{interaction.user.mention} の認証が完了しました。\nコード: {self.code}")
                    else:
                        await interaction.followup.send("認証に失敗しました。コードが確認できませんでした。", ephemeral=True)
        except Exception:
            embed = discord.Embed(
                title="エラーが発生しました。",
                description=f"問題が発生しました。管理者に連絡してください。\n```python\n{traceback.format_exc()}```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            if self.log_channel:
                error_embed = discord.Embed(
                    title="エラーログが届きました！",
                    description=f"```python\n{traceback.format_exc()}\n```",
                    color=discord.Color.red()
                )
                await self.log_channel.send(embed=error_embed)

@tree.command(name="ping", description="pingを計測します")
async def ping(interaction: discord.Interaction):
    ping = client.latency
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    embed = discord.Embed(
        title="Ping",
        description=f"Ping : {ping*1000:.2f}ms\nCPU : {cpu_percent}%\nMemory : {mem.percent}%",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

keep_alive()
client.run(os.getenv("discord"))
