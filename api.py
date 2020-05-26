from flask import Flask, Response, render_template, request, redirect
from threading import Thread
from time import sleep
from main import *
import sqlite3 as sql
import csv

app = Flask(__name__)

stop_run = False
test_false = True
socket_usage = False


def my_function(client, slaves, old_orders):
    print("I'm in thread #1 ")
    global stop_run
    start_time = time.time()
    while not stop_run:
        old_orders = looping_engine(client, slaves, old_orders)
        end = time.time()
        print("time elasped in thread 1 = " + str(end - start_time) + " sec")


def my_function2(file_name, client, slaves, old_orders, Thread_num):
    print("I'm in thread #" + Thread_num)
    global stop_run
    start_time = time.time()
    while not stop_run:
        copy_market(client, slaves, file_name)
        end = time.time()
        print("time elasped in thread" + Thread_num + " = " + str(end - start_time) + " sec")


def on_order_caller(event):
    # callback for event new order
    if not event['e'] == "executionReport":
        return
    if event['X'] == 'FILLED':
        return
    if event['o'] == 'MARKET':  # if market order we dont have price and I cant calculate quantity
        event['p'] = on_order_caller.slaves[0].connection.get_ticker(symbol=event['s'])['lastPrice']

    print(event)
    for slave in on_order_caller.slaves:
        slave.on_order_handler(event)

def socket_function(master, slaves, old_orders):
    print("Using web socket")
    master_socket = master.create_socket()
    on_order_caller.slaves = slaves   # may be bad solution but its working :D
    con = master_socket.start_user_socket(on_order_caller)
    master_socket.start()
    # set variable for stop socket
    global socket_usage
    socket_usage = True
    set_stop_run.master_socket = master_socket


def manual_run():
    client, slaves, old_orders = server_begin()
    #t1 = Thread(target=my_function ,args=(client, slaves, old_orders,))
    t1 = Thread(target=socket_function, args=(client, slaves, old_orders,))
    #     t2 = Thread(target=my_function2, args=("config_files/symbols.csv",client, slaves, old_orders, "2"))
    #     t3 = Thread(target=my_function2, args=("config_files/symbols2.csv",client, slaves, old_orders, "3"))
    #     t4 = Thread(target=my_function2, args=("config_files/symbols3.csv",client, slaves, old_orders,"4"))
    #     t5 = Thread(target=my_function2, args=("config_files/symbols4.csv",client, slaves, old_orders,"5"))

    t1.start()
    #     t2.start()
    #     t3.start()
    #     t4.start()
    #     t5.start()

    return "Processing"



@app.route("/stop", methods=['GET'])
def set_stop_run():
    global stop_run
    stop_run = True
    #stop if socket
    global socket_usage
    if socket_usage:
        set_stop_run.master_socket.close()
        stop_run = False
        print('WebSocket closed')
    return redirect("/", code=302)


@app.route("/run", methods=['GET'])
def run_process():
    global stop_run
    stop_run = False
    manual_run()
    return redirect("/", code=302)


@app.route('/master', methods=['POST'])
def master_form():
    print(request.form['comment_content'])
    print(request.form['comment_content2'])
    print(request.form['comment_content3'])
    with sql.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("INSERT INTO keys (name,key,secret,type) VALUES (?,?,?,?)", (
        request.form['comment_content3'], request.form['comment_content'], request.form['comment_content2'], "master"))
        con.commit()
        print("Record successfully added")

    con.close()

    return redirect("/", code=302)


@app.route('/delete_master')
def delete_master():
    with sql.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("delete from keys where type='master'")
        con.commit()
        print("Record successfully deleted")
    con.close()
    return redirect("/", code=302)


@app.route('/delete_slave')
def delete_slave():
    with sql.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("delete from keys where type='slave'")
        con.commit()
        print("Record successfully deleted")
    con.close()
    return redirect("/", code=302)


@app.route('/slave', methods=['POST'])
def slave_form():
    print(request.form['comment_content'])
    print(request.form['comment_content2'])
    print(request.form['comment_content3'])
    with sql.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("INSERT INTO keys (name,key,secret,type) VALUES (?,?,?,?)", (
        request.form['comment_content3'], request.form['comment_content'], request.form['comment_content2'], "slave"))
        con.commit()
        print("Record successfully added")
    con.close()
    return redirect("/", code=302)


@app.route('/')
def homepage():
    global test_false

    if test_false == True:
        test_false = False

    final = bool(test_false) ^ bool(stop_run)

    con = sql.connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("select * from keys where type='slave'")
    rows = cur.fetchall()

    cur = con.cursor()
    cur.execute("select * from keys where type='master'")
    rows2 = cur.fetchall()

    slave_keys = []
    slave_sec = []
    master_key = []
    master_sec = []

    for row in rows:
        slave_keys.append(row["key"])
        slave_sec.append(row["secret"])

    for row in rows2:
        master_key.append(row["key"])
        master_sec.append(row["secret"])

    with open('config_files/config.csv', mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Master API Key'] + master_key + [""])
        writer.writerow(['Master API Keys'] + master_sec + [""])
        writer.writerow(['Slave API Keys'] + slave_keys + [""])
        writer.writerow(['Slave API Secrets'] + slave_sec + [""])

    final_str = "No" if False else "Yes"
    return render_template("home.html", isRunning="Is App Running ? : " + final_str, rows=rows, rows2=rows2)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
