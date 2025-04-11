import sys
import os
import json
import time
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from webdriver_manager.chrome import ChromeDriverManager

# 사용자 데이터 저장 파일
USER_DATA_FILE = "data/user.json"

# 사용자 데이터를 저장하는 함수
def save_user_data(user_id, user_pw):
    os.makedirs("data", exist_ok=True)  # data 폴더 생성 (존재하지 않으면)
    with open(USER_DATA_FILE, "w", encoding="utf-8") as file:
        json.dump({"id": user_id, "pw": user_pw}, file)

# 사용자 데이터를 로드하는 함수
def load_user_data():
    if os.path.exists(USER_DATA_FILE):  # user.json 파일이 존재하면
        with open(USER_DATA_FILE, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                return data.get("id", ""), data.get("pw", "")
            except json.JSONDecodeError:
                return "", ""  # JSON 파싱 오류 시 빈 값 반환
    return "", ""  # 파일이 없으면 빈 값 반환

# 로그인 작업을 수행하는 QThread
class LoginWorker(QThread):
    login_finished = pyqtSignal(bool, str)  # 로그인 성공 여부와 메시지 전달

    def __init__(self, user_id, user_pw):
        super().__init__()
        self.user_id = user_id
        self.user_pw = user_pw
        self.cnt = 0

    def run(self):
        try:
            options = webdriver.ChromeOptions()
            # options.add_argument("--headless")  # 백그라운드 실행
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--start-maximized")

            driver = webdriver.Chrome(options=options)

            url = "https://gw.suresofttech.com/login"
            driver.get(url)
            time.sleep(2)

            id_box = driver.find_element(By.NAME, "username")
            pw_box = driver.find_element(By.NAME, "password")

            id_box.send_keys(self.user_id)
            time.sleep(1)
            pw_box.send_keys(self.user_pw)
            time.sleep(1)
            pw_box.send_keys(Keys.RETURN)

            time.sleep(5)  # 로그인 후 페이지 로딩 대기

            if "https://gw.suresofttech.com/app/home" in driver.current_url:  # 로그인 성공 여부 확인 (URL 변경 체크)
                save_user_data(self.user_id, self.user_pw)  # 로그인 성공 시 ID, PW 저장
                self.login_finished.emit(True, "로그인 성공! ID/PW 저장 완료")
            else:
                self.login_finished.emit(False, "로그인 실패! 아이디 또는 비밀번호를 확인하세요.")

            time.sleep(2)
            
            driver.get("https://gw.suresofttech.com/app/ehr")
            
            time.sleep(5)
            
            wait = WebDriverWait(driver, 10)
            # tb_attend_body 내부 요소가 로드될 때까지 대기
            
            day_areas = driver.find_elements(By.ID, "day_area")

            # display:none이 없는 요소 찾기
            visible_day_area = None
            for area in day_areas:
                style_attr = area.get_attribute("style")
                if not style_attr or "display:none" not in style_attr.replace(" ", ""):
                    visible_day_area = area
                    break  # 찾으면 종료

            # visible_day_area 내부에서 day_list 찾기
            if visible_day_area:
                try:
                    parent_element = visible_day_area.find_element(By.ID, "day_list")
                    print("day_list 요소를 찾았습니다!")

                    # tb_attend_list 요소들 찾기
                    list_elements = parent_element.find_elements(By.CLASS_NAME, "tb_attend_list")

                    # 요소 개수 출력 (디버깅용)
                    print(f"찾은 tb_attend_list 개수: {len(list_elements)}")

                    # 각 항목의 데이터 가져오기
                    for index, element in enumerate(list_elements):
                        try:
                            # 각각의 내부 요소 찾기
                            date_element = element.find_element(By.CLASS_NAME, "date_l").find_element(By.CLASS_NAME, "txt")
                            day_element = element.find_element(By.CLASS_NAME, "date_r").find_element(By.CLASS_NAME, "txt")
                            s_time_element = element.find_element(By.CLASS_NAME, "attend").find_element(By.CLASS_NAME, "txt")
                            e_time_element = element.find_element(By.CLASS_NAME, "leave").find_element(By.CLASS_NAME, "txt")
                            total_time_element = element.find_element(By.CLASS_NAME, "total_time").find_element(By.CLASS_NAME, "txt")

                            # 텍스트 가져오기 (textContent 활용)
                            date = date_element.get_attribute("textContent").strip()
                            day = day_element.get_attribute("textContent").strip()
                            s_time = s_time_element.get_attribute("textContent").split("IP :")[0].strip()
                            e_time = e_time_element.get_attribute("textContent").split("IP :")[0].strip()
                            total_time = total_time_element.get_attribute("textContent").strip()

                            print(f"{index + 1}번째 데이터 - 날짜: {date}, 요일: {day}, 출근시간: {s_time}, 퇴근시간 : {e_time}, 총 근무시간 : {total_time}")
                            self.cnt += 1
                            if self.cnt == 5:
                                break

                        except Exception as e:
                            print(f"{index + 1}번째 데이터에서 오류 발생: {e}")
                except:
                    print("day_list 요소를 찾을 수 없습니다.")
            else:
                print("display:none이 없는 day_area를 찾을 수 없습니다.")
            
            
            

            time.sleep(100)

            driver.quit()

        except Exception as e:
            self.login_finished.emit(False, f"오류 발생: {str(e)}")

# UI 클래스
class LoginUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("로그인")
        self.setGeometry(100, 100, 300, 180)

        self.label_id = QLabel("ID:")
        self.label_pw = QLabel("Password:")
        self.input_id = QLineEdit(self)
        self.input_pw = QLineEdit(self)
        self.input_pw.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_login = QPushButton("로그인", self)
        self.btn_login.clicked.connect(self.start_login)

        self.status_label = QLabel("")  # 로그인 상태 메시지 표시

        layout = QVBoxLayout()
        layout.addWidget(self.label_id)
        layout.addWidget(self.input_id)
        layout.addWidget(self.label_pw)
        layout.addWidget(self.input_pw)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # user.json이 있으면 ID/PW 로드하여 자동 입력
        user_id, user_pw = load_user_data()
        self.input_id.setText(user_id)
        self.input_pw.setText(user_pw)

    def start_login(self):
        user_id = self.input_id.text()
        user_pw = self.input_pw.text()

        if not user_id or not user_pw:
            self.status_label.setText("ID와 비밀번호를 입력하세요.")
            return

        self.status_label.setText("로그인 중...")

        # QThread 실행 (웹 로그인)
        self.login_worker = LoginWorker(user_id, user_pw)
        self.login_worker.login_finished.connect(self.handle_login_result)
        self.login_worker.start()

    def handle_login_result(self, success, message):
        if success:
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setStyleSheet("color: red;")
        self.status_label.setText(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginUI()
    window.show()
    sys.exit(app.exec())
