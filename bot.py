import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import os

# Aktifkan intent message_content agar bot dapat membaca pesan command
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Konfigurasi global simpan data input
config = {
    "token": os.environ.get("DISCORD_BOT_TOKEN"),  # Ambil token dari environment variable
    "channel_id": None,
    "message": None,
    "delay": None,
    "posting_active": False,
}

# Simpan channel terakhir dari perintah/tombol Start untuk auto post
last_autopost_channel_id = None

class SetTokenModal(Modal):
    def __init__(self):
        super().__init__(title="Set Akun & Konfigurasi Bot")

        self.token_input = TextInput(
            label="Discord Bot Token",
            style=discord.TextStyle.short,
            placeholder="Masukkan token bot",
            required=True,
            default=config.get("token", ""), # Isi default token dari config jika ada
        )
        self.channel_id_input = TextInput(
            label="Channel ID (kosongkan untuk channel saat ini)",
            style=discord.TextStyle.short,
            placeholder="ID channel tujuan",
            required=False,
            default=str(config["channel_id"]) if config["channel_id"] else "",
        )
        self.message_input = TextInput(
            label="Pesan",
            style=discord.TextStyle.paragraph,
            placeholder="Pesan yang akan dikirim",
            required=True,
            default=config["message"] if config["message"] else "",
        )
        self.delay_input = TextInput(
            label="Jeda (detik)",
            style=discord.TextStyle.short,
            placeholder="Jeda waktu dalam detik",
            required=True,
            default=str(config["delay"]) if config["delay"] else "60",
        )

        self.add_item(self.token_input)
        self.add_item(self.channel_id_input)
        self.add_item(self.message_input)
        self.add_item(self.delay_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            token_val = self.token_input.value.strip()
            channel_id_text = self.channel_id_input.value.strip()
            channel_id_val = int(channel_id_text) if channel_id_text else None
            message_val = self.message_input.value.strip()
            delay_val = int(self.delay_input.value.strip())
        except ValueError:
            await interaction.response.send_message("Input Channel ID atau Jeda tidak valid. Pastikan mereka adalah angka.", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"Terjadi kesalahan: {e}", ephemeral=True)
            return

        config["token"] = token_val
        config["channel_id"] = channel_id_val
        config["message"] = message_val
        config["delay"] = delay_val

        await interaction.response.send_message(
            f"✅ **Konfigurasi berhasil disimpan!**\n\n"
            f"**Token:** `[Tersimpan]`\n"
            f"**Channel ID:** `{channel_id_val or 'Channel Saat Ini'}`\n"
            f"**Jeda:** `{delay_val}` detik\n"
            f"**Pesan:**\n``````",
            ephemeral=True,
        )


class AutoPostView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Set Token", style=discord.ButtonStyle.blurple)
    async def set_token_button(self, interaction: discord.Interaction, button: Button):
        modal = SetTokenModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cek Account", style=discord.ButtonStyle.gray)
    async def cek_account_button(self, interaction: discord.Interaction, button: Button):
        if not config["token"]:
            await interaction.response.send_message("❌ Token belum diatur.", ephemeral=True)
            return
        await interaction.response.send_message("✅ Token sudah tersimpan.", ephemeral=True)

    @discord.ui.button(label="Status Posting", style=discord.ButtonStyle.gray)
    async def status_posting_button(self, interaction: discord.Interaction, button: Button):
        status = "Aktif" if config["posting_active"] else "Tidak Aktif"
        await interaction.response.send_message(f"Status auto post: **{status}**", ephemeral=True)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green)
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if config["posting_active"]:
            await interaction.response.send_message("❌ Auto-post sudah berjalan.", ephemeral=True)
            return

        if not all([config["token"], config["message"], config["delay"]]):
            await interaction.response.send_message(
                "❌ Konfigurasi belum lengkap. Silakan tekan tombol 'Set Token' terlebih dahulu.", ephemeral=True
            )
            return

        global last_autopost_channel_id

        channel_id_to_use = config["channel_id"] or interaction.channel.id
        last_autopost_channel_id = channel_id_to_use

        config["posting_active"] = True
        auto_post_task.change_interval(seconds=config["delay"])
        auto_post_task.start()

        await interaction.response.send_message(f"✅ Auto-post dimulai di channel ID `{channel_id_to_use}`.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        if not config["posting_active"]:
            await interaction.response.send_message("❌ Auto-post belum berjalan.", ephemeral=True)
            return

        config["posting_active"] = False
        auto_post_task.cancel()

        await interaction.response.send_message("✅ Auto-post dihentikan.", ephemeral=True)


@tasks.loop(seconds=10)
async def auto_post_task():
    if not bot.is_ready():
        return

    if not config["posting_active"]:
        return

    channel_id = last_autopost_channel_id or config.get("channel_id")
    if not channel_id:
        print("Channel ID belum ditentukan, tidak bisa mengirim pesan.")
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"Channel dengan ID {channel_id} tidak ditemukan.")
        return

    try:
        await channel.send(config["message"])
        print(f"Auto post terkirim di channel {channel_id}")
    except Exception as e:
        print(f"Gagal mengirim pesan: {e}")

@auto_post_task.before_loop
async def before_auto_post():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"Bot sudah siap sebagai {bot.user} ({bot.user.id})")

@bot.command()
async def autopost(ctx):
    view = AutoPostView()
    await ctx.send(content="**⚙️ Pengaturan Auto Post**\nSilakan gunakan tombol di bawah untuk mengelola bot.", view=view)


bot.run(config["token"])
