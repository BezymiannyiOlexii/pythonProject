import os
import socket
from flask import Flask, render_template, request, redirect

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    HOST = "127.0.0.1"
    PORT = 65431
    uploaded_file = request.files['file']
    raw = uploaded_file.read()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Client Sending flag")
        flag: int = 1
        s.send(flag.to_bytes(1, 'big'))
        print("Client Sending:", uploaded_file.filename)

        s.sendall(len(uploaded_file.filename).to_bytes(4, 'big'))
        s.sendall(uploaded_file.filename.encode('ascii'))
        s.sendall(len(raw).to_bytes(8, 'big'))
        s.sendall(raw)
    print("Received")
    return redirect('/upload')

@app.route('/download')
def download_file():

    HOST = "127.0.0.1"
    PORT = 65431
    filename = request.args['name']

    if request.args["action"] == "upl":
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))

            print("Client Sending flag")
            flag: int = 2
            s.send(flag.to_bytes(1, 'big'))

            print('Client Receiving')
            with s:

                s.sendall(len(filename).to_bytes(4, 'big'))
                s.sendall(filename.encode())

                expected_size = b""
                while len(expected_size) < 8:
                    more_size = s.recv(8 - len(expected_size))
                    if not more_size:
                        raise Exception("Short file length received")
                    expected_size += more_size
                expected_size = int.from_bytes(expected_size, 'big')

                packet = b""
                while len(packet) < expected_size:
                    buffer = s.recv(expected_size - len(packet))
                    if not buffer:
                        raise Exception("Incomplete file received")
                    packet += buffer
                filename = '/Users/macbookair/Downloads_python/' + filename
                with open(filename, 'wb') as f:
                    f.write(packet)
        return redirect('/disk')
    elif request.args["action"] == "del":
        os.remove('data/'+filename)
        return redirect('/disk')
    else:
        return redirect('/disk')


@app.route('/disk', methods=['GET'])
def disk():
    database_files = os.listdir('data/')
    database_sizes = list()
    for file in database_files:
        file_size = os.path.getsize('data/'+file)
        if file_size > 10**9:
            file_size /= 1024**3
            file_weight = 'Gb'
            size = '%.2f'%file_size+' {}'.format(file_weight)
        elif file_size > 10**6:
            file_size /= 1024**2
            file_weight = 'MB'
            size = '%.2f' % file_size + ' {}'.format(file_weight)
        else:
            file_size /= 1024
            file_weight = 'kB'
            size = '%.2f' % file_size + ' {}'.format(file_weight)

        database_sizes.append(size)
    print(database_files, database_sizes)
    data = zip(database_files, database_sizes)
    return render_template('disk.html', data=data)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=4446, debug=True)

