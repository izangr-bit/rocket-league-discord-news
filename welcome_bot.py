
import os
import discord

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
WELCOME_CHANNEL_ID = 1563857865716793367

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"✅ Bot de bienvenida conectado: {client.user}")


@client.event
async def on_member_join(member):
    channel = client.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        try:
            channel = await client.fetch_channel(WELCOME_CHANNEL_ID)
        except discord.HTTPException as error:
            print(f"No pude encontrar el canal: {error}")
            return

    embed = discord.Embed(
        title="🚀 ¡Un nuevo piloto aterriza!",
        description=(
            f"¡Bienvenido/a {member.mention} al servidor!\n\n"
            "🎮 Prepárate para jugar, conocer gente y disfrutar.\n"
            "🏁 ¡Que empiece la partida!"
        ),
        color=discord.Color.orange()
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Ya somos {member.guild.member_count} miembros")

    try:
        await channel.send(
            content=f"👋 ¡Hey, {member.mention}!",
            embed=embed
        )
        print(f"Bienvenida enviada a {member}")
    except discord.HTTPException as error:
        print(f"No pude enviar la bienvenida: {error}")


if not TOKEN:
    raise RuntimeError("Falta configurar DISCORD_BOT_TOKEN")

client.run(TOKEN)
