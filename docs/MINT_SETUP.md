# Linux Mint setup — from zero to diagnosing the car

Everything in order: Kimi CLI (optional AI assistant on the machine), the
app, Bluetooth adapter, first run. Tested path on Linux Mint 21+.

## 1. System packages

```bash
sudo apt update
sudo apt install -y git python3-tk python3-serial bluez rfcomm
```

## 2. Kimi Code CLI — the AI assistant on the Mint laptop (optional)

The Kimi desktop app is Windows/Mac only; the **CLI** is the Linux version.
It is *not* needed to run the diagnostics app — it is there to fix, extend
and explain things on the machine itself.

```bash
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
# open a NEW terminal, then:
kimi --version
kimi            # first run: type /login and sign in with your Kimi account
```

Note: the CLI has its own session and does not share history with the
desktop app on other machines. After cloning the repo (next step), start it
inside the project folder and it will read the README/docs to get up to
speed.

## 3. The diagnostics app

```bash
git clone https://github.com/jobluemann/ford-tdci-recovery.git
cd ford-tdci-recovery
pip3 install -r requirements.txt        # just pyserial

# try it with the built-in fake car — no hardware, no keys:
python3 gui_app.py
```

## 4. AI assistant key (one time, free)

In the app: click **AI Setup** → follow the link to console.groq.com →
create a free key → paste it → **Save + Test** → green ✓.
(Or `cp .env.example .env`, fill in the key, and
`export $(grep -v '^#' .env | xargs)` before launching.)

The key is stored in `data/ai_config.json` on that machine only — it is
git-ignored and never leaves the laptop.

## 5. Bluetooth ELM327 adapter

Adapter in the car, ignition ON, then:

```bash
bash scripts/mint_bluetooth_setup.sh    # pairs, binds /dev/rfcomm0, permissions
```

Details and troubleshooting: `docs/BLUETOOTH_SETUP.md`.

## 6. First real run

```bash
python3 gui_app.py --real               # port: /dev/rfcomm0 → Connect
```

Then press the buttons in order: **1. Backup snapshot** (always first),
**2. Read fault codes**, **3. Module scan**. The DEM (AWD) module needs an
adapter with an HS/MS-CAN switch — see `docs/ADAPTERS.md`.

## Updating later

```bash
cd ford-tdci-recovery && git pull
```
