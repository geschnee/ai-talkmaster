import smtplib
from fastapi import FastAPI, Request, status
import httpx
from fastapi.responses import JSONResponse

from datetime import datetime

from email.message import EmailMessage

# Import the email modules we'll need
from email.mime.text import MIMEText

from code.aitalkmaster_utils import log
from code.shared import app, config

EMAIL_RECEIVER = "log@hypergrid.net"
EMAIL_SENDER = "autosender2048@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

app_user=EMAIL_SENDER
with open("app_password.txt", "r") as file:
    app_pwd=file.read()


def getEmailContent(log_24h: bool, filter_contents: list):
    with open("logfile.txt", "r") as file:
        content = file.read()


    # Filter lines that contain startConversation logs
    lines = content.splitlines()

    filtered_lines = []

    for line in lines:
        included=False
        for filter in filter_contents:
            if filter in line:
                included=True

        if included:
            filtered_lines.append(line)

    content = "\n".join(filtered_lines)

    if log_24h:
        lines = content.splitlines()
        filtered = []

        for r in lines:
            if len(r) < 20:
                continue
            timestring = r[0:16]
            

            logTime = datetime.strptime(timestring, '%Y-%m-%d %H:%M')

            timeDiff = datetime.now() - logTime
            hours = timeDiff.total_seconds() / 3600
            if hours < 24:
                filtered.append(r)

        if len(filtered) > 0:
            content = "\n".join(filtered)
            result = f'LLM Server log filtered for information 24 hours:\n{content}'
        else:
            result = f'LLM Server log filtered for information 24 hours: There were no new conversations in the last 24h.'
    else:

        result = f'LLM Server log filtered for information (full file):\n{content}'

    return result


def sendEmail(log_24h: bool, subject: str, filters: list):

    try:
        result = getEmailContent(log_24h, filters)

        log("email content: " + result)

        msg = EmailMessage()
        msg.set_content(result)

        # me == the sender's email address
        # you == the recipient's email address
        msg['Subject'] = 'LLM Server Log File'
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        # Prepare actual message
        # message = """From: %s\nTo: %s\nSubject: %s\n\n%s""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(app_user, app_pwd)
        #server.sendmail(FROM, TO, message)
        server.send_message(msg)
        server.quit()

        return JSONResponse(
            status_code=200,
            content={"message": "Email has been sent to " + EMAIL_RECEIVER}
        )
    except Exception as e:
        log(f'[Email] Error executing command: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": e}
        )

# TODO add more filters to email method

@app.post("/email24h")
async def email24h(request: Request):
    return sendEmail(log_24h=True, subject="LLM Server Log File", filters=["startConversation:", "noMemorySendMessage:" ,"memorySendMessage:"])

@app.post("/emailfull")
async def emailfull(request: Request):
    return sendEmail(log_24h=False, subject="LLM Server Log File", filters=["startConversation:", "noMemorySendMessage:" ,"memorySendMessage:"])