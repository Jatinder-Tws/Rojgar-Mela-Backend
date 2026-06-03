import httpx
print(httpx.post('http://localhost:8000/api/attendance/mark', json={'email': 'kuldeepkumar3729@gmail.com', 'date': '2026-06-03', 'status': 'Absent'}).json())
