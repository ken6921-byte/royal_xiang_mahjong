import sqlite3
import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'royal_xiang_final_v8_del'
DB_NAME = "mahjong.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  players_data TEXT, 
                  dong_qian INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def get_rankings():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT players_data FROM records")
    rows = c.fetchall()
    conn.close()
    scores = {}
    for row in rows:
        try:
            data_list = json.loads(row[0]) 
            for p in data_list:
                name = p['name']
                score = int(p['score'])
                scores[name] = scores.get(name, 0) + score
        except:
            continue
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name FROM players ORDER BY name")
    players = [row[0] for row in c.fetchall()]
    c.execute("SELECT * FROM records ORDER BY date DESC LIMIT 10")
    raw_records = c.fetchall()
    conn.close()
    records = []
    for r in raw_records:
        records.append({
            "date": r[1],
            "data": json.loads(r[2]),
            "dong": r[3]
        })
    rankings = get_rankings()
    return render_template('index.html', players=players, records=records, rankings=rankings)

@app.route('/history')
def history():
    filter_name = request.args.get('player_name')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name FROM players ORDER BY name")
    players = [row[0] for row in c.fetchall()]
    c.execute("SELECT * FROM records ORDER BY date DESC")
    raw_records = c.fetchall()
    conn.close()
    filtered_records = []
    for r in raw_records:
        data_list = json.loads(r[2])
        if filter_name and filter_name != "全部":
            found = False
            for p in data_list:
                if p['name'] == filter_name:
                    found = True
                    break
            if not found:
                continue
        filtered_records.append({
            "date": r[1],
            "data": data_list,
            "dong": r[3]
        })
    return render_template('history.html', players=players, records=filtered_records, current_filter=filter_name)

@app.route('/players')
def manage_players():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM players ORDER BY name")
    players = c.fetchall()
    conn.close()
    return render_template('players.html', players=players)

@app.route('/rename_player', methods=['POST'])
def rename_player():
    player_id = request.form.get('player_id')
    new_name = request.form.get('new_name')
    if not player_id or not new_name:
        return redirect(url_for('manage_players'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE id = ?", (player_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return redirect(url_for('manage_players'))
    old_name = result[0]
    
    try:
        c.execute("UPDATE players SET name = ? WHERE id = ?", (new_name, player_id))
        c.execute("SELECT id, players_data FROM records")
        all_records = c.fetchall()
        for row in all_records:
            record_id = row[0]
            data_json = row[1]
            try:
                data_list = json.loads(data_json)
                updated = False
                for p in data_list:
                    if p['name'] == old_name:
                        p['name'] = new_name
                        updated = True
                if updated:
                    new_json = json.dumps(data_list, ensure_ascii=False)
                    c.execute("UPDATE records SET players_data = ? WHERE id = ?", (new_json, record_id))
            except:
                continue
        conn.commit()
    except sqlite3.IntegrityError:
        pass 
    conn.close()
    return redirect(url_for('manage_players'))

# 🔥 新增：刪除玩家功能 🔥
@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 只刪除名單，不刪除歷史紀錄
    c.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_players'))

@app.route('/add_player', methods=['POST'])
def add_player():
    name = request.form.get('new_player_name')
    if name:
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO players (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            pass
    return redirect(url_for('index'))

@app.route('/add_record', methods=['POST'])
def add_record():
    player_names = request.form.getlist('player_name[]')
    player_scores = request.form.getlist('player_score[]')
    dong = int(request.form.get('dong_qian') or 0)

    record_data = []
    total_score = 0
    
    for i in range(len(player_names)):
        name = player_names[i]
        try:
            score = int(player_scores[i])
        except:
            score = 0
        if name and name != "":
            record_data.append({"name": name, "score": score})
            total_score += score

    if total_score + dong != 0:
        return f"<script>alert('帳目不平！玩家總分({total_score}) + 東錢({dong}) 應該要等於 0'); window.history.back();</script>"

    if len(record_data) < 2:
         return f"<script>alert('至少要有兩位玩家才能記帳！'); window.history.back();</script>"

    json_data = json.dumps(record_data, ensure_ascii=False)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO records (players_data, dong_qian) VALUES (?, ?)", (json_data, dong))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)