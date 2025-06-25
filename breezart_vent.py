# -*- coding: utf-8 -*-
import sys
import socket
import time
import json

TCP_IP: str = '192.168.XX.XX' # IP пульта вент. установки
TCP_PORT: int = 1560 # Номер порта, по умолчанию 1560
TCP_PASS: int = 00000 # Пароль (десятичное число)
BUFFER_SIZE: int = 256

def send_request(cmd) -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0) # Ожидание ответа 5 сек.
        s.connect((TCP_IP, TCP_PORT))
        s.send(cmd.encode())
        data = s.recv(BUFFER_SIZE).decode()
        s.close()
        time.sleep(0.6)  # Интервал между запросами не менее 500 мс
        return data
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

def parse_status(resp) -> dict:
    '''
    Парсер статуса
    '''
    parts = resp.strip().split("_")
    if len(parts) < 11:
        return {"error": "Invalid response", "raw": resp}

    # Parse all fields as integers
    bitState = int(parts[1], 16)
    bitMode = int(parts[2], 16)
    bitTempr = int(parts[3], 16)
    bitHumid = int(parts[4], 16)
    bitSpeed = int(parts[5], 16)
    bitMisc = int(parts[6], 16)
    bitTime = int(parts[7], 16)
    bitDate = int(parts[8], 16)
    bitYear = int(parts[9], 16)
    msg = parts[10]


    status = {}
    # bitState
    status['pwr_btn_state'] = bool(bitState & (1 << 0)) # состояние питания (вкл./выкл.)
    status['has_warning'] = bool(bitState & (1 << 1)) # есть предупреждение.
    status['has_fatal_error'] = bool(bitState & (1 << 2)) # есть фатальная ошибка.
    status['danger_overheat'] = bool(bitState & (1 << 3)) # угроза перегрева калорифера.
    status['auto_off'] = bool(bitState & (1 << 4)) # установка автоматически выключена на 5 минут для автоподстройки нуля датчика давления.
    status['change_filter'] = bool(bitState & (1 << 5)) # предупреждение о необходимости замены фильтра.
    status['mode_set'] = (bitState >> 6) & 0x7  # установленный режим работы. 1 – Обогрев 2 – Охлаждение 3 – Авто 4 – Отключено (вентиляция без обогрева и охлаждения)
    status['humid_mode'] = bool(bitState & (1 << 9)) # селектор Увлажнитель активен (стоит галочка)
    status['speed_is_down'] = bool(bitState & (1 << 10)) # скорость вентилятора автоматически снижена.
    status['func_restart'] = bool(bitState & (1 << 11)) # включена функция Рестарт при сбое питания.
    status['func_comfort'] = bool(bitState & (1 << 12)) # включена функция Комфорт.
    status['humid_auto'] = bool(bitState & (1 << 13)) # увлажнение включено (в режиме Авто).
    status['scen_block'] = bool(bitState & (1 << 14)) # сценарии заблокированы режимом ДУ.
    status['btn_pwr_block'] = bool(bitState & (1 << 15)) # кнопка питания заблокирована режимом ДУ.
    # bitMode
    unit_state = bitMode & 0b11
    status['unit_state'] = unit_state  # состояние установки: 0 – Выключено. 1 – Включено. 2 – Выключение (переходный процесс перед отключением). 3 – Включение (переходный процесс перед включением).
    status['unit_state_str'] = ["Выключено", "Включено", "Выключение", "Включение"][unit_state]
    status['power'] = unit_state == 1
    status['scen_allow'] = bool(bitMode & (1 << 2))  # разрешена работа по сценариям.
    status['mode'] = (bitMode >> 3) & 0b111  # режим работы: 0 – Обогрев 1 – Охлаждение 2 – Авто-Обогрев 3 – Авто-Охлаждение 4 – Отключено (вентиляция без обогрева и охлаждения) 5 – Нет (установка выключена)
    status['mode_str'] = ["Обогрев", "Охлаждение", "Авто-Обогрев", "Авто-охлаждение", "Вентиляция", "Нет", "unknown", "unknown"][(bitMode >> 3) & 0b111]
    status['num_active_scen'] = (bitMode >> 6) & 0b1111  # номер активного сценария (от 1 до 8), 0 если нет.
    status['who_activate_scen'] = (bitMode >> 10) & 0b111  # кто запустил (активировал) сценарий: 0 – активного сценария нет и запущен не будет 1 – таймер1, 2 – таймер2, 3 – пользователь вручную, 4 – сценарий будет запущен позднее (сейчас активного сценария нет)
    status['who_activate_scen_str'] = ["Нет", "Таймер 1", "Таймер 2", "Вручную", "Планировщик", "unknown", "unknown", "unknown"][(bitMode >> 10) & 0b111]
    status['num_ico_hf'] = (bitMode >> 13) & 0b111  # номер иконки Влажность / фильтр.
    # bitTempr
    current_temp = bitTempr & 0xFF
    target_temp = (bitTempr >> 8) & 0xFF
    status['current_temp'] = current_temp if current_temp < 128 else current_temp - 256  # signed char – текущая температура, °С. Диапазон значений от -50 до 70.
    status['target_temp'] = target_temp  # заданная температура, °С. Диапазон значений от 0 до 50.
    # bitHumid
    current_hum = bitHumid & 0xFF
    target_hum = (bitHumid >> 8) & 0xFF
    status['current_hum'] = current_hum # текущая влажность (при наличии увлажнители или датчика влажности). Диапазон значений от 0 до 100. При отсутствии данных значение равно 255.
    status['target_hum'] = target_hum # заданная влажность. Диапазон значений от 0 до 100.
    # bitSpeed
    status['fan_speed'] = bitSpeed & 0xF  # текущая скорость вентилятора, диапазон от 0 до 10.
    status['fan_speed_target'] = (bitSpeed >> 4) & 0xF  # заданная скорость вентилятора, диапазон от 0 до 10.
    status['fan_speed_fact'] = (bitSpeed >> 8) & 0xFF  # фактическая скорость вентилятора 0 – 100%. Если не определено, то 255.
    # bitMisc
    status['temp_min'] = bitMisc & 0xF  # минимально допустимая заданная температура (от 5 до 15). Может изменяться в зависимости от режима работы вентустановки
    status['color_msg'] = (bitMisc >> 4) & 0x3  # иконка сообщения Msg для различных состояний установки: 0 – Нормальная работа (серый) 1 – Предупреждение (желтый) 2 – Ошибка (красный)
    status['color_msg_str'] = ["Нормально", "Предупреждение", "Ошибка", "unknown"][(bitMisc >> 4) & 0x3]
    status['color_ind'] = (bitMisc >> 6) & 0x3  # цвет индикатора на кнопке питания для различных состояний установки: 0 – Выключено (серый) 1 – Переходный процесс включения / отключения (желтый) 2 – Включено (зеленый)
    status['color_ind_str'] = ["Выключено", "Переходный процесс включения / отключения", "Включено", "unknown"][(bitMisc >> 6) & 0x3]
    status['filter_dust'] = (bitMisc >> 8) & 0xFF  # загрязненность фильтра 0 - 250%, если не определено, то 255.
    # bitTime
    status['minute'] = bitTime & 0xFF # минуты (от 00 до 59)
    status['hour'] = (bitTime >> 8) & 0xFF # часы (от 00 до 23)
    # bitDate
    status['day'] = bitDate & 0xFF # день месяца (от 1 до 31)
    status['month'] = (bitDate >> 8) & 0xFF # месяц (от 1 до 12)
    # bitYear
    status['dow'] = bitYear & 0xFF # день недели (от 1-Пн до 7-Вс)
    status['dow_str'] = ["Пн", "Вт", "Ср", "Чт", "Пят", "Суб", "Вс"][(bitYear & 0xFF) - 1] if 1 <= (bitYear & 0xFF) <= 7 else "unknown"
    status['year_short'] = (bitYear >> 8) & 0xFF # год (от 0 до 99, последние две цифры года).
    # Сообщение
    status['msg'] = msg # текстовое сообщение о состоянии установки длиной от 5 до 70 символов.
    return status

def parse_sensors(resp) -> dict:
    '''
    Парсер сенсоров
    '''
    parts = resp.strip().split("_")
    if len(parts) < 9:
        return {"error": "Invalid response", "raw": resp}
    sensors = {}
    def parse_temp(val):
        v = int(val, 16)
        # Обработка отсутствия данных
        if v == 0xFB07:
            return None
        # signed word: если старший бит установлен, это отрицательное число
        if v & 0x8000:
            v = v - 0x10000
        return v / 10.0

    def parse_hum(val):
        v = int(val, 16)
        if v == 0xFB07:
            return None
        return v / 10.0

    sensors['t_inf'] = parse_temp(parts[1]) # signed word – температура воздуха на выходе вентустановки х 10, °С. Диапазон значений от -50,0 до 70,0. При отсутствии корректных данных значение равно 0xFB07
    sensors['h_inf'] = parse_hum(parts[2]) # влажность воздуха на выходе вентустановки x 10. Диапазон значений от 0,0 до 100,0. При отсутствии корректных данных значение равно 0xFB07.
    sensors['t_room'] = parse_temp(parts[3]) # температура воздуха в помещении
    sensors['h_room'] = parse_hum(parts[4]) # влажность воздуха в помещении
    sensors['t_out'] = parse_temp(parts[5]) # температура наружного воздуха
    sensors['h_out'] = parse_hum(parts[6]) # влажность наружного воздуха
    sensors['thf'] = parse_temp(parts[7]) # температура теплоносителя
    pwr = int(parts[8], 16)
    sensors['pwr'] = None if pwr == 0xFB07 else pwr / 1000 # потребляемая калорифером мощность, кВт (от 0 до 65.5).
    return sensors

def parse_fixed_params(resp) -> dict:
    '''
    Парсер фиксированных параметров
    '''
    parts = resp.strip().split("_")
    if len(parts) < 8:
        return {"error": "Invalid response", "raw": resp}
    params = {}
    # bitTempr
    bitTempr = int(parts[1], 16)
    params['temp_min'] = bitTempr & 0xFF # минимально допустимая заданная температура (от 5 до 15)
    params['temp_max'] = (bitTempr & 0xFF00) >> 8 # максимально допустимая заданная температура (от 30 до 45)
    # bitSpeed
    bitSpeed = int(parts[2], 16)
    params['speed_min'] = bitSpeed & 0xFF # минимальная скорость (от 1 до 7).
    params['speed_max'] = (bitSpeed & 0xFF00) >> 8 # максимальная скорость (от 2 до 10).
    # bitHumid
    bitHumid = int(parts[3], 16)
    params['humid_min'] = bitHumid & 0xFF # минимальная заданная влажность, от 0 до 100%.
    params['humid_max'] = (bitHumid & 0xFF00) >> 8 # максимальная заданная влажность, от 0 до 100%.
    # bitMisc
    bitMisc = int(parts[4], 16)
    params['n_vav_zone'] = bitMisc & 0x1F # кол-во зон в режиме VAV (от 1 до 20).
    params['vav_mode'] = bool(bitMisc & (1 << 8)) # режим VAV включен.
    params['is_reg_press_vav'] = bool(bitMisc & (1 << 9)) # включена возможность регулирования давления в канале в режиме VAV.
    params['is_show_hum'] = bool(bitMisc & (1 << 10)) # включено отображение влажности.
    params['is_casc_reg_t'] = bool(bitMisc & (1 << 11)) # включен каскадный регулятор T.
    params['is_casc_reg_h'] = bool(bitMisc & (1 << 12)) # включен каскадный регулятор H.
    params['is_humid'] = bool(bitMisc & (1 << 13)) # есть увлажнитель.
    params['is_cooler'] = bool(bitMisc & (1 << 14)) # есть охладитель.
    params['is_auto'] = bool(bitMisc & (1 << 15)) # eсть режим Авто переключения Обогрев / Охлаждение.
    # BitPrt
    bitPrt = int(parts[5], 16)
    params['prot_subvers'] = bitPrt & 0xFF # убверсия протокола обмена (от 1 до 255)
    params['prot_vers'] = (bitPrt & 0xFF00) >> 8 # версия протокола обмена (от 100 до 255)
    # BitVerTPD
    bitVerTPD = int(parts[6], 16)
    params['lo_ver_tpd'] = bitVerTPD & 0xFF # младший байт версии прошивки пульта
    params['hi_ver_tpd'] = (bitVerTPD & 0xFF00) >> 8 # старший байт версии прошивки пульта
    # BitVerContr
    params['firmware_ver'] = int(parts[7], 16) # версия прошивки контроллера
    return params

def status() -> None:
    cmd = f"VSt07_{TCP_PASS:X}"
    resp = send_request(cmd)
    parsed = parse_status(resp)
    print(json.dumps(parsed, ensure_ascii=False))

def sensors() -> None:
    cmd = f"VSens_{TCP_PASS:X}"
    resp = send_request(cmd)
    parsed = parse_sensors(resp)
    print(json.dumps(parsed, ensure_ascii=False))

def fixed_params() -> None:
    cmd = f"VPr07_{TCP_PASS:X}"
    resp = send_request(cmd)
    parsed = parse_fixed_params(resp)
    print(json.dumps(parsed, ensure_ascii=False))

def power(state) -> None:
    # state: "on", "off", "true", "false", "1", "0", "11", "10"
    s = str(state).strip().lower()
    if s in ("on", "true", "1", "11"):
        mode = 11
    elif s in ("off", "false", "0", "10"):
        mode = 10
    else:
        print(json.dumps({"error": f"Unknown power state: {state}"}))
        return

    cmd = 'VWPwr_{0:X}_{1:X}'.format(TCP_PASS, mode)
    print(f"DEBUG: Sending command: {cmd}")
    resp = send_request(cmd)
    print(json.dumps({
        "power": state,
        "cmd": cmd,
        "response": resp
    }))

def speed(s) -> None:
    s_min = 1
    s_max = 10
    try:
        s_int = int(s)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Unknown speed state: {s}"}))
        return
    if not (s_min <= s_int <= s_max):
        print(json.dumps({"error": f"Unknown speed state ({s_min} - {s_max}): {s_int}"}))
        return
    cmd = 'VWSpd_{0:X}_{1:X}'.format(TCP_PASS, s_int)
    resp = send_request(cmd)
    print(json.dumps({"speed": s_int, "response": resp}))

def temperature(s) -> None:
    s_min = 5
    s_max = 45
    try:
        s_int = int(s)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Unknown temperature state: {s}"}))
        return
    if not (s_min <= s_int <= s_max):
        print(json.dumps({"error": f"Unknown temperature state ({s_min} - {s_max}): {s_int}"}))
        return
    cmd = 'VWTmp_{0:X}_{1:X}'.format(TCP_PASS, s_int)
    resp = send_request(cmd)
    print(json.dumps({"temperature": s_int, "response": resp}))

def humidity(s) -> None:
    s_min = 0
    s_max = 100
    try:
        s_int = int(s)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Unknown humidity state: {s}"}))
        return
    if not (s_min <= s <= s_max):
        print(json.dumps({"error": f"Unknown humidity state ({s_min} - {s_max}): {s_int}"}))
        return
    cmd = 'VWHum_{0:X}_{1:X}'.format(TCP_PASS, s_int)
    resp = send_request(cmd)
    print(json.dumps({"humidity": s_int, "response": resp}))

def set_feature(mode=None, humid=None, comfort=None, restart=None):
    """
    mode: 1-Обогрев, 2-Охлаждение, 3-Авто, 4-Отключено, None - не менять
    humid: 1-Вкл(Авто), 2-Выкл, None - не менять
    comfort: 1-Вкл, 2-Выкл, None - не менять
    restart: 1-Вкл, 2-Выкл, None - не менять
    """
    bitFeature = 0
    # ModeSet (бит 0-2)
    if mode in (1, 2, 3, 4):
        bitFeature |= (mode & 0x7)
    # HumidSet (бит 3-4)
    if humid in (1, 2):
        bitFeature |= ((humid & 0x3) << 3)
    # Comfort (бит 5-6)
    if comfort in (1, 2):
        bitFeature |= ((comfort & 0x3) << 5)
    # Restart (бит 7-8)
    if restart in (1, 2):
        bitFeature |= ((restart & 0x3) << 7)
    cmd = 'VWFtr_{0:X}_{1:X}'.format(TCP_PASS, bitFeature)
    resp = send_request(cmd)
    print(json.dumps({"cmd": cmd, "bitFeature": bitFeature, "response": resp}))
    return resp

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: breezart_vent.py [status | sensors | fixed_params | power on or off | speed 1-10 | temperature 5-45 | humidity 0-100 | set_feature mode humid comfort restart]")
        sys.exit(1)
    action = sys.argv[1]
    if action == "power" and len(sys.argv) > 2:
        power(sys.argv[2])
    elif action == "status":
        status()
    elif action == "sensors":
        sensors()
    elif action == "fixed_params":
        fixed_params()
    elif action == "speed" and len(sys.argv) > 2:
        speed(sys.argv[2])
    elif action == "temperature" and len(sys.argv) > 2:
        temperature(sys.argv[2])
    elif action == "humidity" and len(sys.argv) > 2:
        humidity(sys.argv[2])
    elif action == "set_feature" and len(sys.argv) > 2:
        def parse_arg(idx):
            try:
                val = int(sys.argv[idx])
                return val
            except (IndexError, ValueError):
                return None
        mode = parse_arg(2)
        humid = parse_arg(3)
        comfort = parse_arg(4)
        restart = parse_arg(5)
        set_feature(mode, humid, comfort, restart)
    else:
        print("Unknown command")
        sys.exit(1)