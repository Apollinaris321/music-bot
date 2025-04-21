- a command can only be executed if the last one finishes
- depends on priority 
- commands with a lower priority cant kick off commands with a higher priority



HOW SYSTEMD SERVICES ARE RUN:

Okay, let's create the systemd service file for your intro_bot.py and list the necessary systemctl commands.
First, I noticed a couple of small typos in your music_bot.service example (awlays -> always, jounral -> journal). I've corrected those in the template below.
1. Create the intro_bot.service file:
Filename: Use a distinct name like discord-intro-bot.service.
Command:
sudo nano /etc/systemd/system/discord-intro-bot.service
Use code with caution.
Bash
Paste the following content, ensuring the paths are correct for your setup:
[Unit]
# Change the description to match the new bot
Description=Discord Intro Bot Service (intro_bot.py)
After=network.target

[Service]
User=root
Group=root

# Working directory should be the same
WorkingDirectory=/root/discord_bot

# *** IMPORTANT: Change ExecStart to point to intro_bot.py ***
ExecStart=/root/discord_bot/musicvenv/bin/python3 /root/discord_bot/experimental/intro_bot.py

# Corrected typo: always
Restart=always
RestartSec=5

StandardOutput=journal
# Corrected typo: journal
StandardError=journal

# Assuming intro_bot.py uses the same SIGTERM handler
KillSignal=SIGTERM
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
Use code with caution.
Ini
Save and Close: Ctrl+X, Y, Enter.
2. systemctl Commands for Managing the New Service:
You'll use these commands in your terminal (via SSH) to control the intro_bot. Replace discord-intro-bot.service with the exact filename you used.
Reload systemd: (Essential after creating or editing any service file)
sudo systemctl daemon-reload
Use code with caution.
Bash
Enable: (Make the service start automatically on server boot)
sudo systemctl enable discord-intro-bot.service
Use code with caution.
Bash
Disable: (Prevent the service from starting automatically on boot)
sudo systemctl disable discord-intro-bot.service
Use code with caution.
Bash
Start: (Start the service now)
sudo systemctl start discord-intro-bot.service
Use code with caution.
Bash
Stop: (Stop the service now - sends SIGTERM first)
sudo systemctl stop discord-intro-bot.service
Use code with caution.
Bash
Restart: (Stop the service then start it again)
sudo systemctl restart discord-intro-bot.service
Use code with caution.
Bash
Status: (Check if it's running, see recent logs, PID, etc.)
sudo systemctl status discord-intro-bot.service
Use code with caution.
Bash
(Press q to exit the status view)
View Logs: (See the detailed output logged via journald)
sudo journalctl -u discord-intro-bot.service
Use code with caution.
Bash
Add -f to follow live logs: sudo journalctl -u discord-intro-bot.service -f (Ctrl+C to exit)
Add -n 50 to see the last 50 lines: sudo journalctl -u discord-intro-bot.service -n 50