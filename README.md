0. Створити venv
    python3.9 -m venv venv
    source venv/bin/activate
    
1. Встановити Python 3.9
    sudo apt install python3.9

2. Встановити Pip
    sudo apt install python3-pip

3. Встановити i2c-tools
    sudo apt install -y i2c-tools

4. Встановити pyserial
    pip install pyserial

5. Налаштувати автозапуск
    sudo cp PigfarmApp.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable PigfarmApp

6. Встановити FTP server
    sudo apt install vsftpd
    sudo nano /etc/vsftpd.conf
        ...
        local_root=/home/pi/app/receipt/
    sudo systemctl restart vsftpd

