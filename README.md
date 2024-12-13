# GIA_KokoroColor

KokoroColorは、Arduino Uno R3とRaspberry Piを組み合わせ、心拍数と湿度のデータに基づいてPhilips Hue Goの照明色を制御するプロジェクトです。
群馬イノベーションアワードのファイナル審査にて使用するために作成しました。

## 構成

- **arduino.ino**: Arduino Uno R3用のコードで、心拍数と湿度のセンサーデータを取得し、シリアル通信でRaspberry Piに送信します。
- **main.py**: Raspberry Pi上で動作するPythonスクリプトで、Arduinoから受信したデータを解析し、BLE（Bluetooth Low Energy）を介してPhilips Hue Goの色を制御します。

## Raspberry Piでの自動起動設定

Raspberry Piの起動時に`main.py`を自動的に実行するには、`systemd`を使用します。以下の手順で設定を行います。

1. **サービスファイルの作成**:
   ```bash
   sudo vim /etc/systemd/system/kokorocolor.service
   ```
   以下の内容を入力します。
   ```ini
   [Unit]
   Description=KokoroColor Service

   [Service]
   ExecStart=/usr/bin/python3.11 /home/pi/path/to/main.py

   [Install]
   WantedBy=multi-user.target
   ```
   ※`ExecStart`と`WorkingDirectory`のパスは`main.py`の実際のパスに置き換えてください。

2. **サービスの有効化と起動**:
   ```bash
   sudo systemctl enable kokorocolor.service
   sudo systemctl start kokorocolor.service
   ```
   これで、Raspberry Piの起動時に`main.py`が自動的に実行されるようになります。

詳細は、以下の記事を参考にしてください。
https://zenn.dev/bonsai_engineer/articles/3cd836a5c649fe


## Philips Hue GoとのBLE接続

Philips Hue GoとBLE接続する際、接続が切断される問題が報告されています。この問題を回避するため、以下の手順でデバイスを設定します。

1. **デバイスのスキャン**:
   ```bash
   bluetoothctl
   scan on
   ```
   目的のデバイスのMACアドレスを確認します。

2. **デバイスのペアリング**:
   ```bash
   pair <MACアドレス>
   ```

3. **デバイスへの接続**:
   ```bash
   connect <MACアドレス>
   ```

4. **デバイスの信頼設定**:
   ```bash
   trust <MACアドレス>
   ```

これらの手順により、接続の安定性が向上します。詳細は、以下のStack Overflowの投稿を参照してください。
https://stackoverflow.com/questions/65948825/cant-send-command-to-ble-device-philips-hue-bulb-connection-drops
