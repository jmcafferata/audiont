import csv
from datetime import datetime

# sends a message when the user isn't subscribed // envía un mensaje cuando el usuario no está suscrito
async def sendSubscribeMessage(update):
    # create a row on logs.csv with the date, time and username of the user that sent the voice note // crear una fila en logs.csv con la fecha, hora y nombre de usuario del usuario que envió la nota de voz
    with open('logs.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), update.message.from_user.username])
    # send the user a message saying they are not subscribed // enviarle al usuario un mensaje diciendo que no está suscrito
    await update.message.reply_text('No estás suscrito. Para suscribirte, contactá a @jmcafferata o creá tu propio bot de Telegram usando el código de este repositorio.')
    await update.message.reply_text('github.com/jmcafferata/audiont')
