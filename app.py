# 運行以下程式需安裝模組: line-bot-sdk, flask, pyquery
# 安裝方式，輸入指令:
# pip install line-bot-sdk flask pyquery
# 本機端測試 Linebot 檢核表
# 1. 啟動ngrok: .ngrok http 5001
# 2. 將網址更新到 Line 後台的 Webhook URL
# 3. 啟動應用程式 點擊vscode右上角的撥放鍵

from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
    LocationMessage,
)

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    LocationMessageContent,
)

import os
from modules.reply import faq, menu
from modules.currency import get_exchange_table

from openai import OpenAI
client = OpenAI(
    api_key= os.environ.get("OPENAI_KEY")

)

table = get_exchange_table()
print("匯率表", table)

app = Flask(__name__)

configuration = Configuration(access_token=os.environ.get("LINE_ACCESS_TOCKEN"))
handler = WebhookHandler(os.environ.get("LINE_SECRET"))

@app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    # app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)  
def handle_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入文字訊息時
        line_bot_api = MessagingApi(api_client)
        # 在此的 evnet.message.text 即是 Line Server 取得的使用者文字訊息
        user_msg = event.message.text
    
        print("#" * 30)
       
        print("使用者傳入的文字訊息是:", user_msg)
        print("#" * 30)
        bot_msg = TextMessage(text=f"What you said is: {user_msg}")
        if user_msg in ["貼圖"]:
            bot_msg = StickerMessage(packageId="789" ,stickerId="10856")
        
        if user_msg in faq:
            bot_msg = faq[user_msg]
        elif user_msg in ["menu", "選單"]:
            bot_msg = menu
        elif user_msg in table:
            buy = table[user_msg]["buy"]
            sell = table[user_msg]["sell"]
            bot_msg = TextMessage(text = f"{user_msg}\n 買價: {buy}\n 賣價:{sell}\n 引用來源:台灣銀行匯率牌價公告")
        else:
            completion = client.chat.completions.create(
                   model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": """
                         你是一個服務型AI能根據使用者的問題親切地回答
                         如果使用者不知道如何使用請提示使用者可以輸入menu查看選單
                         """},
                        {
                        "role": "user",
                        "content": user_msg
                        }
                     ]
            )
            ai_msg = completion.choices[0].message.content
            print("AI語言模型回應", ai_msg )
            bot_msg = TextMessage(text=ai_msg)


        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                # 放置於 ReplyMessageRequest 的 messages 裡的物件即是要回傳給使用者的訊息
                # 必須注意由於 Line 有其使用的內部格式
                # 因此要回覆的訊息務必使用 Line 官方提供的類別來產生回應物件
                messages=[
                    bot_msg
                ]
            )
        )

@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入貼圖時
        line_bot_api = MessagingApi(api_client)
        sticker_id = event.message.sticker_id
        package_id = event.message.package_id
        keywords_msg = "這張貼圖背後沒有關鍵字"
        if event.message.keywords:
            if len(event.message.keywords) > 0:
                keywords_msg = "這張貼圖的關鍵字有:"
                keywords_msg += ", ".join(event.message.keywords)
        # 可以使用的貼圖清單
        # https://developers.line.biz/en/docs/messaging-api/sticker-list/
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    StickerMessage(package_id="6325", sticker_id="10979904"),
                    TextMessage(text=f"你剛才傳入了一張貼圖，以下是這張貼圖的資訊:"),
                    TextMessage(text=f"貼圖包ID為 {package_id} ，貼圖ID為 {sticker_id} 。"),
                    TextMessage(text=keywords_msg),
                ]
            )
        )

@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入地理位置時
        line_bot_api = MessagingApi(api_client)
        latitude = event.message.latitude
        longitude = event.message.longitude
        address = event.message.address
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"You just sent a location message."),
                    TextMessage(text=f"The latitude is {latitude}."),
                    TextMessage(text=f"The longitude is {longitude}."),
                    TextMessage(text=f"The address is {address}."),
                    LocationMessage(title="Here is the location you sent.", address=address, latitude=latitude, longitude=longitude)
                ]
            )
        )

# 如果應用程式被執行執行
if __name__ == "__main__":
    print("[伺服器應用程式開始運行]")
    # 取得遠端環境使用的連接端口，若是在本機端測試則預設開啟於port=5001
    port = int(os.environ.get('PORT', 5001))
    print(f"[Flask即將運行於連接端口:{port}]")
    print(f"若在本地測試請輸入指令開啟測試通道: ./ngrok http {port} ")
    # 啟動應用程式
    # 本機測試使用127.0.0.1, debug=True
    # Heroku部署使用 0.0.0.0
    app.run(host="0.0.0.0", port=port, debug=True)
