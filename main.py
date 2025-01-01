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
        
    guild = interaction.guild.id
    guild_settings[guild] = {
        "channel": channel,
        "role": role,
        "log_channel": log_channel
    }

    button = discord.ui.Button(emoji="✅", label="認証する", style=discord.ButtonStyle.primary, custom_id="authorize")
    view = discord.ui.View()
    view.add_item(button)
    
    embed = discord.Embed(
        title="このサーバーに参加するためには、認証が必要です！",
        description="下の「✅認証する」ボタンを押して、認証を開始してください。",
    )
    
    await channel.send(embed=embed, view=view)
    
    await tree.sync()
    print("起動!")

@client.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.data['component_type'] == 2:
            await on_button_click(interaction)
    except KeyError:
        pass

def random_code(length):
    alphanumeric_chars = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_chars) for _ in range(length))

class AuthorizeView(discord.ui.View):
    def __init__(self, code, timeout=300):
        super().__init__(timeout=timeout)
        self.code = code
    
    @discord.ui.button(emoji="✅", label="書き込んだ", style=discord.ButtonStyle.primary)
    async def writed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://viper.2ch.sc/news4vip/dat/1717936187.dat") as response:
			data = await response.read()
			# 文字コードを検出
　　　　　　　encoding = chardet.detect(data)['encoding']
　　　　　　　# Shift-JISでデコード
　　　　　　　dat = data.decode(encoding)
            guild = interaction.guild
            if self.code in dat:
                role = guild_settings[guild.id]["role"]
                await interaction.user.add_roles(role)
                log_channel = guild_settings[guild.id]["log_channel"]
                await log_channel.send(f"{interaction.user.mention} の認証が完了しました。")
                await interaction.followup.send("**認証が完了しました。**", ephemeral=True)
                await guild.text_channels[0].send(f"{interaction.user.mention} の認証が完了しました。\nコード: {self.code}")
            else:
                await interaction.followup.send("認証に失敗しました。", ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="エラーが発生しました。",
                description=f"エラーは <@1209770634628825130> に報告されました。修正されるのをお待ち下さい。\n```python\n{traceback.format_exc()}```",
                color=discord.Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(os.getenv("errorlog_webhook"), session=session)
                embed = discord.Embed(
                    title="エラーログが届きました！",
                    description=f"エラーが発生しました。\n以下、トレースバックです。```python\n{traceback.format_exc()}\n```"
                )
                await webhook.send(embed=embed)
                
async def on_button_click(interaction: discord.Interaction):
    custom_id = interaction.data["custom_id"]
    try:
        if custom_id == "authorize":
            # ユーザーが認証済みかどうかを確認
            role = guild_settings[interaction.guild.id]["role"]
            if not any(r.id == role.id for r in interaction.user.roles):  # ユーザーにロールが付与されていない場合
                code = random_code(10)
                view = AuthorizeView(code, timeout=300)
                embed = discord.Embed(
                    title="サーバーに参加するためには、認証が必要です",
                    description=f"5分以内に、[２ch.net復活させようぜw のスレッド](https://viper.2ch.sc/test/read.cgi/news4vip/1717936187/) ( https://viper.2ch.sc/test/read.cgi/news4vip/1717936187/ )にて、以下の内容を投稿してください。投稿したあと、「✅書き込んだ」ボタンを教えて下さい。\n```\nDiscord支部の認証用文字列です: {code}\n```",
                    color=discord.Colour.purple()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="あなたは既に認証しています！",
                    description="",
                    color=discord.Colour.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="エラーが発生しました。",
            description=f"エラーは <@1209770634628825130> に報告されました。修正されるのをお待ち下さい。\n```python\n{traceback.format_exc()}```",
            color=discord.Colour.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(os.getenv("errorlog_webhook"), session=session)
            embed = discord.Embed(
                title="エラーログが届きました！",
                description=f"エラーが発生しました。\n以下、トレースバックです。```python\n{traceback.format_exc()}\n```"
            )
            await webhook.send(embed=embed)

@tree.command(name="ping", description="pingを計測します")
async def ping(interaction: discord.Interaction):
    ping = client.latency
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory() 
    embed = discord.Embed(title="Ping", description=f"Ping : {ping*1000}ms\nCPU : {cpu_percent}%\nMemory : {mem.percent}%", color=discord.Colour.gold())
    embed.set_thumbnail(url=client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

keep_alive()
client.run(os.getenv("discord"))
