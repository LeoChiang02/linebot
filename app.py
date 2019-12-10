import os
import sys
import csv

from flask import Flask, jsonify, request, abort, send_file
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from fsm import TocMachine
from utils import send_text_message

load_dotenv()


machine = TocMachine(
    states=["user", "state1", "state2"],
    transitions=[
        {
            "trigger": "advance",
            "source": "user",
            "dest": "state1",
            "conditions": "is_going_to_state1",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "state2",
            "conditions": "is_going_to_state2",
        },
        {"trigger": "go_back", "source": ["state1", "state2"], "dest": "user"},
    ],
    initial="user",
    auto_transitions=False,
    show_conditions=True,
)

app = Flask(__name__, static_url_path="")


# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        
            
        try:
            message = str(event.message.text)
            [mode,start,target,ml]=message.split('/')
            message="ok"
            start=eval(start)
            ml=eval(ml)
            target=eval(target)
            
            if target>0 and ml>0:
                if mode == 'a' or mode == "稀釋":
                    if target < start or ml<0:
                        ans=target*ml/start
                        others=ml-ans
                        message='母液濃度:'+str(start)+'M /目標濃度:'+str(target)+'M /所需劑量: '+str(ml)+' mL'
                        sol='配法: 將'+str(ans)+' mL母液加入'+str(others)+' mL溶劑'
                    else:
                        message="input conc. invalid"

                if mode == 'b' or mode == "配置":
                    if  start>0 :
                        ans=target*ml/start
                        others=ml-ans
                        message='溶質分子量:'+str(start)+'M /目標濃度:'+str(target)+'M /所需劑量: '+str(ml)+' mL'
                        sol='配法: 將'+str(ans)+' mL母液加入'+str(others)+' mL溶劑'
                    else:
                        message="input molarity invalid"
            else:
                message="condition invalid"
            
        except:
            message="input invalid"

        if message=="input invalid":
            line_bot_api.reply_message(event.reply_token , TextSendMessage(text="<歡迎使用溶液配置計算機>"+
                                                                            "\n"+'模式: 稀釋(a) 配置(b)'+                                                                                         
                                                                            "\n"+'  稀釋/ 母液濃度(M) / 目標濃度(M) / 所需劑量(mL)'
                                                                            "\n"+'  配置/ 溶質分子量(g/mol) /目標濃度(M) / 所需劑量(mL)'
                                                                            "\n"+'輸入範例:'+
                                                                            "\n"+'ex: a/20/5/20 [稀釋:20 M->5 M 需要20 mL]'
                                                                            ))   
        elif message=="input conc. invalid":
            line_bot_api.reply_message(event.reply_token , TextSendMessage(text=message))
        else:
            line_bot_api.reply_message(event.reply_token , TextSendMessage(text=message+"\n"+sol))
    
  
        
 
           

        
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook_handler():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        if not isinstance(event.message.text, str):
            continue
        print(f"\nFSM STATE: {machine.state}")
        print(f"REQUEST BODY: \n{body}")
        response = machine.advance(event)
        if response == False:
            send_text_message(event.reply_token, "Not Entering any State")

    return "OK"


@app.route("/show-fsm", methods=["GET"])
def show_fsm():
    machine.get_graph().draw("fsm.png", prog="dot", format="png")
    return send_file("fsm.png", mimetype="image/png")


if __name__ == "__main__":
    port = os.environ.get("PORT", 8000)
    app.run(host="0.0.0.0", port=port, debug=True)
