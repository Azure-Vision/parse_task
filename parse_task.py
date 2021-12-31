#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import datetime
import json
import re
import subprocess

import os
import pytz
import streamlit as st
import random

# from debug import debug, mark

def get_args():
    parser = argparse.ArgumentParser(description='Parse task')
    parser.add_argument('-t', '--todo', type=str, required=False, default="", help='Task to parse')
    parser.add_argument('--no_print', default=False, action = "store_true", help='Task to parse')
    parser.add_argument('--no_add', default=False, action = "store_true", help='Task to parse')
    parser.add_argument('--db_id', default="")
    parser.add_argument('--integration_token', default="")
    args = parser.parse_args()
    return args
args = get_args()
if "db_id" in os.environ:
    args.db_id = os.environ["db_id"]
if "integration_token" in os.environ:
    args.integration_token = os.environ["integration_token"]
def insert_page_to_notion(todo, status, start_time, end_time, args):
    # 添加页
    curl_command_add = """curl -X POST https://api.notion.com/v1/pages \
        -H "Authorization: Bearer %s" \
        -H "Content-Type: application/json" \
        -H "Notion-Version: 2021-05-13" \
        --data '""" % args.integration_token
    input_json = """{
            "parent": {
                "database_id": "%s"
            },
            "properties": {
                "任务": {
                    "title": [{
                        "text": {
                            "content": "%s"
                        }
                    }]
                },
                "状态": {
                    "select": {
                        "name": "%s"
                    }
                }""" % (args.db_id, todo, status)
    if start_time != None:
        input_json += """,
                "时间": {
                    "date": {
                        "start": "%s",
                        "end": %s
                    }
                }
            }
        }""" % (start_time, end_time)
    else:
        input_json += """
            }
        }"""
    curl_command_add = curl_command_add + input_json + "'"
    if not args.no_print:
        st.write("input json:")
        st.write(json.loads(input_json))
        print("input json:")
        print(input_json)
    output = subprocess.getoutput(curl_command_add)
    output = "{" + "{".join(output.split("{")[1:])
    try:
        result_page_id = json.loads(output)["id"]
    except Exception:
        result_page_id = "failed"
    st.write("result page id:")
    st.write(result_page_id)
    return result_page_id


def next_weekday(day: datetime.date, weekday):
    """weekday: 1 for Monday and 7 for Sunday"""
    days_ahead = weekday - 1 - day.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return day + datetime.timedelta(days_ahead)
def parse_date(todo, args):
    date = None
    today = datetime.date.today()
    if re.search(r"(今天?)|(tod(ay)?)", todo):
        date = datetime.date.today()
        todo = re.sub(r"(今天?)|(tod(ay)?)", "", todo)
    elif re.search(r"(明天?)|(tom(morrow)?)", todo):
        date = datetime.date.today() + datetime.timedelta(days=1)
        todo = re.sub(r"(明天?)|(tom(morrow)?)", "", todo)
    elif re.search(r"后天?", todo):
        date = datetime.date.today() + datetime.timedelta(days=2)
        todo = re.sub(r"后天?", "", todo)
    elif re.search(r"((下?周)|(下?星期))[一二三四五六七日1234567]", todo):
        date_str = re.search(r"((下?周)|(下?星期))[一二三四五六七日1234567]", todo).group()
        todo = todo.replace(date_str, "")
        if date_str[-1] == "一" or date_str[-1] == "1":
            date = next_weekday(datetime.date.today(), 1)
        elif date_str[-1] == "二" or date_str[-1] == "2":
            date = next_weekday(datetime.date.today(), 2)
        elif date_str[-1] == "三" or date_str[-1] == "3":
            date = next_weekday(datetime.date.today(), 3)
        elif date_str[-1] == "四" or date_str[-1] == "4":
            date = next_weekday(datetime.date.today(), 4)
        elif date_str[-1] == "五" or date_str[-1] == "5":
            date = next_weekday(datetime.date.today(), 5)
        elif date_str[-1] == "六" or date_str[-1] == "6":
            date = next_weekday(datetime.date.today(), 6)
        elif date_str[-1] == "七" or date_str[-1] == "7" or date_str[-1] == "日":
            date = next_weekday(datetime.date.today(), 7)
    elif re.search(r"((\d{4}|明)年)?(\d{1,2}|(下个?)|(本|今))(月|\.)(\d{1,2})?(日|号)?", todo):
        date_obj = re.search(r"((\d{4}|明)年)?(\d{1,2}|(下个?)|(本|今))(月|\.)(\d{1,2})?(日|号)?", todo)
        if date_obj.group(2) is not None:
            if date_obj.group(2) == "明":
                year = today.year + 1
            else:
                year = int(date_obj.group(2))
        else:
            year = today.year
        
        if date_obj.group(4) is not None:
            month = today.month + 1
        elif date_obj.group(5) is not None:
            month = today.month
        else:
            month = int(date_obj.group(3))
        
        if date_obj.group(7) is not None:
            day = int(date_obj.group(7))
        else:
            day = 1
        date = datetime.date(year, month, day)
        todo = re.sub(r"((\d{4}|明)年)?(\d{1,2}|(下个?)|(本|今))(月|\.)(\d{1,2})?(日|号)?", "", todo)
    elif re.search(r"(\d{1,2})(日|号)", todo):
        date_obj = re.search(r"(\d{1,2})(日|号)", todo)
        date = datetime.date(today.year, today.month, int(date_obj.group(1)))
        todo = re.sub(r"(\d{1,2})(日|号)", "", todo)
    if not args.no_print:
        print(f"date: {date}")
        st.write(f"date: {date}")
    return todo, date, today


def parse_time(todo, args):
    time = None
    time_re_str = r"((上午)|(早上|早晨))?((下午)|(晚上))?(\d{1,2})(点|时|\:|：)(\d{1,2}|半)?(分)?"
    if re.search(time_re_str, todo):
        time_obj = re.search(time_re_str, todo)
        hour = int(time_obj.group(7))
        if hour < 12 and time_obj.group(4) is not None:
            hour += 12
        if not time_obj.group(9):
            minute = 0
        elif time_obj.group(9) == "半":
            minute = 30
        else:
            minute = int(time_obj.group(9))
        time = datetime.time(hour, minute)
        todo = todo.replace(time_obj.group(), "")
    elif re.search(r"早(上|晨)?", todo):
        time = datetime.time(8, 0)
        todo = re.sub(r"早(上|晨)?", "", todo)
    elif re.search(r"上午", todo):
        time = datetime.time(9, 0)
        todo = re.sub(r"上午", "", todo)
    elif re.search(r"中午", todo):
        time = datetime.time(12, 0)
        todo = re.sub(r"中午", "", todo)
    elif re.search(r"下午", todo):
        time = datetime.time(14, 0)
        todo = re.sub(r"下午", "", todo)
    elif re.search(r"晚上", todo):
        time = datetime.time(19, 0)
        todo = re.sub(r"晚上", "", todo)
    
    if not args.no_print:
        print(f"time: {time}, todo: {todo}")
        st.write(f"time: {time}, todo: {todo}")

    return todo, time


def parse_date_time(todo, args):
    time = None
    todo, date, today = parse_date(todo, args)
    todo, time = parse_time(todo, args)
    local_timezone = pytz.timezone('Asia/Shanghai')
    if not date and not time:
        start_time = None
    elif date is not None and time is not None:
        start_time = datetime.datetime.combine(date, time, tzinfo=local_timezone)
    elif date is not None:
        # start_time = datetime.datetime.combine(date, datetime.time(0, 0), tzinfo=local_timezone)
        start_time = date
    elif time is not None:
        start_time = datetime.datetime.combine(today, time, tzinfo=local_timezone)
    # start_time = start_time.replace(tzinfo=local_timezone)
    if start_time != None:
        start_time_str = start_time.isoformat()
    else:
        start_time_str = None
    if not args.no_print:
        print(f"start_time: {start_time_str}, todo: {todo}")
        st.write(f"start_time: {start_time_str}, todo: {todo}")
        if type(start_time) == datetime.datetime or type(start_time) == datetime.date:
            st.date_input("start_time", start_time)
        if type(start_time) == datetime.datetime or type(start_time) == datetime.time:
            st.time_input("start_time", start_time)
    end_time_str = "null"
    return start_time_str, end_time_str, todo


def parse_status(todo, start_time, args):
    if start_time is not None:
        status = "提醒 / 日程"
    else:
        status = "收集箱📦"

    if re.search(r"~长期(待办)?", todo):
        status = "长期待办"
        todo = re.sub(r"~长期(待办)?", "", todo)
    elif re.search(r"~可能(清单)?", todo):
        status = "可能清单"
        todo = re.sub(r"~可能(清单)?", "", todo)
    elif re.search(r"~(作业)|~(一?周)(内(完成)?)?", todo):
        status = "一周内完成"
        todo = re.sub(r"~(作业)|~(一?周)(内(完成)?)?", "", todo)
    elif re.search(r"~等(待(他人)?)?", todo):
        status = "等待他人"
        todo = re.sub(r"~等(待(他人)?)?", "", todo)
    if not args.no_print:
        print(f"status: {status}, todo: {todo}")
        st.write(f"status: {status}, todo: {todo}")
    return status, todo


def parse_task(todo, args):
    start_time, end_time, todo = parse_date_time(todo, args)
    status, todo = parse_status(todo, start_time, args)
    return todo, start_time, end_time, status


def get_curl_result(curl_command):
    output = subprocess.getoutput(curl_command)
    output = "{" + "{".join(output.split("{")[1:])
    output = re.sub("[0-9]{3} [ 0-9a-z:]*[0-9]{5}",
                    "", output, count=0, flags=0)
    output_list = output.split("\n")
    output = ""
    for _ in output_list:
        if len(_) > 5:
            output += _
    return output


def save_snippets_list(result):
    snippets_list = []
    for snippet in result:
        title, tag, sentence = "", "", ""
        try:
            title = snippet["properties"]["标题"]['title'][0]["plain_text"]
        except Exception:
            pass
        try:
            sentence = snippet["properties"]["内容"]["rich_text"][0]["plain_text"]
        except Exception:
            pass
        try:
            tag = snippet["properties"]["标签"]["multi_select"][0]["name"]
        except Exception:
            pass
        snippets_list.append(f"【{title}】（{tag}） {sentence}")
    snippets = "\n".join(snippets_list)
    with open("random_snippets.txt", "w") as file:
        file.write(snippets)


def update_block_content(content):
    content = "  ".join(content.split("\n"))
    json_string = '''{
            "text": [{ 
            "text": { "content": "''' + content + '''" } 
            }],
            "checked": false
        }'''
    curl_command = """
        curl -X PATCH https://api.notion.com/v1/blocks/e016647341114dc0b370b470798ec67d \
        -H 'Authorization: Bearer 'secret_3ZPuF9UpMOmwxzcSl1At3W4QmllkN9vBd5zA3co5OVQ'' \
        -H "Content-Type: application/json" \
        -H "Notion-Version: 2021-08-16" \
        -X PATCH \
        --data '{
        "to_do": """ + json_string + """
        }'"""
    try:
        output = get_curl_result(curl_command)
    except Exception:
        pass
def random_snippet(input):
    curl_command = """curl -X POST 'https://api.notion.com/v1/databases/3e24e31ba625407196e4fc54bad210a8/query' \
    -H 'Authorization: Bearer '""" + args.integration_token + """'' \
    -H 'Notion-Version: 2021-05-13' \
    -H "Content-Type: application/json" \
        --data '{}'"""
    print(curl_command)
    try:
        output = get_curl_result(curl_command)
        result = json.loads(output)
        file = open("random_snippets.json", "w+")
        file.write(output)
        file.close()
        result = result["results"]
    except Exception:
        file = open("random_snippets.json", "r")
        result = json.load(file)
        result = result["results"]

    save_snippets_list(result)

    snippet = random.choice(result)

    title = snippet["properties"]["标题"]['title'][0]["plain_text"]
    sentence = snippet["properties"]["内容"]["rich_text"][0]["plain_text"]
    tag = snippet["properties"]["标签"]["multi_select"][0]["name"]
    update_block_content(f"【{title}】\n（{tag}）\n {sentence}")

    path = "Macintosh HD:Users:hewanrong:Downloads:liwu.png"
    buttons = """{"🥳","💪"}"""
    random_scripts = """exec osascript <<EOF 
            tell application "System Events" 
                display dialog "处理结果:{}\n\nShow random scripts?" with title "通知" default button 1
                set returnRecord to the result
                display dialog "【{}】\n\n{}" with title "{}" with icon alias "{}" buttons {} default button 1
            end tell
    EOF
    """.format(input, title, sentence, tag + " " + title, path, buttons)
    print(random_scripts)
    os.system(random_scripts)

if __name__ == '__main__':
    if args.todo == "":
        todo = st.text_input("", value = "")
    else:
        todo = args.todo
    if todo != "":
        todo, start_time, end_time, status = parse_task(todo, args)
        if not args.no_add:
            result_page_id = insert_page_to_notion(todo, status, start_time, end_time, args)
            random_snippet(input=result_page_id)
