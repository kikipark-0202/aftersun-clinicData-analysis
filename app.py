from flask import Flask, jsonify, render_template, request
from data import load_and_process_data, compute_subscores

app = Flask(__name__)

try:
    _df = load_and_process_data('/mnt/user-data/uploads/aftersun_Clinic_Data_Template.xlsx')
except Exception:
    _df = load_and_process_data('aftersun_Clinic_Data_Template.xlsx')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/clinics')
def clinics():
    gender = request.args.get('gender', 'all')
    if gender not in ('all', 'male', 'female'):
        gender = 'all'
    return jsonify(compute_subscores(_df, gender))


if __name__ == '__main__':
    app.run(debug=True, port=8080)
