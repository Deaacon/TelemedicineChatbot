import os
import sqlite3
from datetime import datetime
from typing import Any

from scripts.constants import *


def execute_sql_command(command: str, parameters: dict = {}) -> Any:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(command, parameters)

    if command[:6] == "SELECT":
        rezult = cursor.fetchall()
        connection.close()

        if len(rezult) == 1:
            rezult = rezult[0]
        return rezult

    connection.commit()
    connection.close()


def initializate_database():
    if not os.path.isfile(DB_PATH):
        command = """
            CREATE TABLE "DiaryData" (
            "user_id"	INTEGER NOT NULL,
            "date"	DATE NOT NULL,
            "time"	TIME NOT NULL,
            "text"	TEXT NOT NULL)
            """
        execute_sql_command(command)
        command = """
            CREATE TABLE "FormData" (
	        "user_id"	INTEGER NOT NULL,
	        "date"	DATE NOT NULL,
	        "time"	TIME NOT NULL,
	        "state"	TEXT,
	        "temperature"	TEXT,
	        "pressure"	TEXT,
	        "sugar"	TEXT)
            """
        execute_sql_command(command)
        command = """
            CREATE TABLE "IdData" (
	        "user_id"	INTEGER NOT NULL,
	        "username"	TEXT NOT NULL,
	        PRIMARY KEY("user_id"))
            """
        execute_sql_command(command)
        command = """
            CREATE TABLE "StatData" (
	        "user_id"	INTEGER NOT NULL,
	        "date"	DATE NOT NULL,
	        "time"	TIME NOT NULL,
	        "message_type"	TEXT NOT NULL,
	        "text"	TEXT NOT NULL)
            """
        execute_sql_command(command)


def read_username(id: int):
    item = {"id": id}
    sql_query = "SELECT username FROM IdData WHERE (user_id = :id)"
    result = execute_sql_command(sql_query, item)
    if len(result) == 0:
        return None
    result = result[0]
    return result


def write_username(id: int, username: str):
    item = {"user_id": id, "username": username}
    sql_query = "INSERT INTO IdData VALUES (:user_id, :username)"
    execute_sql_command(sql_query, item)


def write_forms(id: int, form_data: dict):
    item = {
        "user_id": id,
        "date": datetime.today().strftime("%y-%m-%d"),
        "time": datetime.today().strftime("%H:%M:%S"),
        "state": form_data["state_user"],
        "pressure": form_data["pressure_user"],
        "temperature": form_data["temperature_user"],
        "blood": form_data["blood_user"],
    }
    sql_query = "INSERT INTO FormData VALUES (:user_id, :date, :time, :state, :pressure, :temperature, :blood)"
    execute_sql_command(sql_query, item)


def read_diary(id: int):
    item = {"user_id": id}
    sql_query = "SELECT date, time, text from DiaryData WHERE (user_id = :user_id)"
    diary_data = execute_sql_command(sql_query, item)
    if type(diary_data) == tuple:
        diary_data = [diary_data]
    return diary_data


def write_diary(id: int, text: str):
    item = {
        "user_id": id,
        "date": datetime.today().strftime("%y-%m-%d"),
        "time": datetime.today().strftime("%H:%M:%S"),
        "text": text,
    }
    sql_query = "INSERT INTO DiaryData VALUES (:user_id, :date, :time, :text)"
    execute_sql_command(sql_query, item)


def write_statistics(id: int, message_type: str, text: str):
    item = {
        "user_id": id,
        "date": datetime.today().strftime("%y-%m-%d"),
        "time": datetime.today().strftime("%H:%M:%S"),
        "message_type": message_type,
        "text": text,
    }
    sql_query = (
        "INSERT INTO StatData VALUES (:user_id, :date, :time, :message_type, :text)"
    )
    execute_sql_command(sql_query, item)
