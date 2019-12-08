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
        
        content=format(event.source.user_id)
        # read mem  
        info=[]
        error="none"
        info_index=-1
        try:
            with open('mem.csv') as f:
                reader=csv.DictReader(f)
                for row in reader:
                    if row==0:
                        info=[[row['user_id'],row['state'],row['time(min:sec)']]]
                    else:
                        info=info+[[row['user_id'],row['state'],row['time(min:sec)']]]

            error="ok"
        except:
            error="error1"

        # vertify user and recgonize stranger 
        
        try:  
        
            for i in range(len(info)):
                if info[i][0]==content:
                    info_index=i
            if info_index < 0:
                info=info+[content,0,0]   
            error=error+"ok"   
        except:
            error=error+"error2"
        
        # save mem    
        try:
            with open('mem.csv','w') as f:
                writer = csv.DictWriter(f, [row['user_id'],row['state'],row['time(min:sec)']])        
                writer.writeheader()
                    for i in range(len(info)):
                         writer.writerow({'user_id':info[i][0], 'state':info[i][1],'time(min:sec)': info[i][2]})
        except:   
            error=error+"error3"
        
        try:
            if info_index < 0:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="hellow new user"+error))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="wellcome back"+event.message.text+error))
        except:
            error="error4"     
           
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error))
        
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
