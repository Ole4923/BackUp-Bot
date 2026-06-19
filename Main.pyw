import discord
from discord.ext import commands
import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import threading

# ---------------- CONFIG ----------------

config = {}
with open("config.txt", "r", encoding="utf-8") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            config[k] = v

TOKEN = config["TOKEN"]
GUILD_ID = int(config["GUILD_ID"])

# ---------------- LANGUAGE ----------------

lang = "de"

TEXT = {
    "de": {
        "backup": "Backup erstellen",
        "restore": "Backup laden",
        "clear": "Logs löschen",
        "toggle": "DE / EN",
        "title": "Discord Backup Tool",
        "loading": "Bitte nicht das Fenster schließen,\nBot lädt!"
    },
    "en": {
        "backup": "Create Backup",
        "restore": "Load Backup",
        "clear": "Clear Logs",
        "toggle": "DE / EN",
        "title": "Discord Backup Tool",
        "loading": "Please do not close this window,\nbot is loading!"
    }
}

def t(key):
    return TEXT[lang][key]

# ---------------- BOT ----------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

log_box = None

def log(msg):
    print(msg)
    if log_box:
        log_box.insert("end", msg + "\n")
        log_box.see("end")

@bot.event
async def on_ready():
    log(f"✅ Bot online: {bot.user}")

# ---------------- BACKUP ----------------

def create_backup_sync():

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        log("❌ Guild nicht gefunden")
        return None

    log("📦 Backup startet...")

    data = {
        "roles": [],
        "categories": [],
        "channels": []
    }

    for r in guild.roles:
        if r.is_default() or r.managed:
            continue

        log(f"➕ Rolle: {r.name}")

        data["roles"].append({
            "name": r.name,
            "color": r.color.value,
            "permissions": r.permissions.value,
            "hoist": r.hoist,
            "mentionable": r.mentionable
        })

    for c in guild.categories:
        log(f"➕ Kategorie: {c.name}")

        data["categories"].append({
            "name": c.name
        })

    for ch in guild.channels:
        log(f"📡 Channel: {ch.name}")

        data["channels"].append({
            "name": ch.name,
            "type": str(ch.type),
            "category": ch.category.name if ch.category else None
        })

    log("📦 Backup fertig")
    return data

# ---------------- SAVE ----------------

def backup_click():

    file = filedialog.asksaveasfilename(defaultextension=".json")
    if not file:
        return

    data = create_backup_sync()

    if not data:
        messagebox.showerror("Error", "Guild nicht gefunden")
        return

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    log("💾 Backup gespeichert")

# ---------------- RESTORE ----------------

loading_popup = None

def show_loading_popup():
    global loading_popup

    loading_popup = ctk.CTkToplevel(root)
    loading_popup.geometry("350x150")
    loading_popup.title("Loading")

    label = ctk.CTkLabel(
        loading_popup,
        text=t("loading"),
        font=("Arial", 14)
    )
    label.pack(expand=True)

    loading_popup.attributes("-topmost", True)
    loading_popup.grab_set()


def close_loading_popup():
    global loading_popup
    if loading_popup:
        loading_popup.destroy()
        loading_popup = None


async def restore_backup(path):

    guild = bot.get_guild(GUILD_ID)

    if not guild:
        log("❌ Guild nicht gefunden")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    log("🚀 Restore startet")

    # WIPE
    for ch in list(guild.channels):
        await ch.delete()
        log(f"🗑 Channel gelöscht: {ch.name}")

    for c in list(guild.categories):
        await c.delete()
        log(f"🗑 Kategorie gelöscht: {c.name}")

    for r in list(guild.roles):
        if r.is_default() or r.managed:
            continue
        await r.delete()
        log(f"🗑 Rolle gelöscht: {r.name}")

    # ROLES
    for r in data["roles"]:
        role = await guild.create_role(
            name=r["name"],
            permissions=discord.Permissions(r["permissions"]),
            colour=discord.Colour(r["color"]) if "color" in r else discord.Colour.default(),
            hoist=r["hoist"],
            mentionable=r["mentionable"]
        )
        log(f"➕ Rolle erstellt: {r['name']}")

    # CATEGORIES
    cat_map = {}
    for c in data["categories"]:
        cat = await guild.create_category(c["name"])
        cat_map[c["name"]] = cat
        log(f"➕ Kategorie erstellt: {c['name']}")

    # CHANNELS
    for ch in data["channels"]:

        cat = cat_map.get(ch["category"])

        if "text" in ch["type"]:
            await guild.create_text_channel(ch["name"], category=cat)
        else:
            await guild.create_voice_channel(ch["name"], category=cat)

        log(f"➕ Channel erstellt: {ch['name']}")

    log("✅ Restore fertig")

# ---------------- LOAD ----------------

def load_click():

    path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not path:
        return

    show_loading_popup()

    async def run():
        try:
            await restore_backup(path)
        finally:
            root.after(0, close_loading_popup)

    bot.loop.create_task(run())

# ---------------- UI ----------------

def clear_logs():
    log_box.delete("1.0", "end")

def toggle_lang():
    global lang
    lang = "en" if lang == "de" else "de"
    update_ui()

def update_ui():
    btn_backup.configure(text=t("backup"))
    btn_restore.configure(text=t("restore"))
    btn_clear.configure(text=t("clear"))
    btn_toggle.configure(text=t("toggle"))
    root.title(t("title"))

def start_gui():

    global root, log_box, btn_backup, btn_restore, btn_clear, btn_toggle

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("650x500")

    frame = ctk.CTkFrame(root)
    frame.pack(pady=10)

    btn_backup = ctk.CTkButton(frame, text="Backup", command=backup_click, width=150)
    btn_backup.grid(row=0, column=0, padx=10, pady=5)

    btn_restore = ctk.CTkButton(frame, text="Restore", command=load_click, width=150)
    btn_restore.grid(row=0, column=1, padx=10, pady=5)

    btn_clear = ctk.CTkButton(frame, text="Clear", command=clear_logs, width=150)
    btn_clear.grid(row=1, column=0, padx=10, pady=5)

    btn_toggle = ctk.CTkButton(frame, text="DE/EN", command=toggle_lang, width=150)
    btn_toggle.grid(row=1, column=1, padx=10, pady=5)

    log_box = ctk.CTkTextbox(root, height=300)
    log_box.pack(fill="both", expand=True, pady=10)

    update_ui()

    root.mainloop()

# ---------------- START ----------------

def run_bot():
    bot.run(TOKEN)

threading.Thread(target=run_bot, daemon=True).start()
start_gui()