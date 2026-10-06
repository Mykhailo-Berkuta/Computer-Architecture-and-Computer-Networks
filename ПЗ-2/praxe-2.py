"""ПЗ-2 (самостійна робота): визначення характеристик обчислювальної системи
за допомогою системних та бібліотечних викликів (Windows).

Використано:
  - WinAPI через ctypes: GetSystemInfo, GlobalMemoryStatusEx, RtlGetVersion, GetSystemTimes
  - реєстр Windows (winreg): дані про процесор
  - WMI (через PowerShell): плата, BIOS, пам'ять, диски, відеокарта, мережа, слоти, кеш
  - стандартні бібліотеки: platform, os, socket, shutil
Результат виводиться на екран і зберігається у system_report.txt
"""
import ctypes
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from ctypes import Structure, byref, c_size_t, c_ulonglong, c_void_p, c_wchar, sizeof
from ctypes.wintypes import DWORD, FILETIME, WORD

lines = []
summary = {}


def out(text=""):
    print(text)
    lines.append(text)


def head(title):
    out(f"\n=== {title} ===")


def row(label, value):
    out(f"  {label}: {value}")


def gb(n):
    try:
        return f"{int(n) / 1024 ** 3:.2f} ГБ"
    except (TypeError, ValueError):
        return "невідомо"


# ---------- виклики WinAPI ----------
class SYSTEM_INFO(Structure):
    _fields_ = [
        ("wProcessorArchitecture", WORD), ("wReserved", WORD),
        ("dwPageSize", DWORD),
        ("lpMinimumApplicationAddress", c_void_p),
        ("lpMaximumApplicationAddress", c_void_p),
        ("dwActiveProcessorMask", c_size_t),
        ("dwNumberOfProcessors", DWORD), ("dwProcessorType", DWORD),
        ("dwAllocationGranularity", DWORD),
        ("wProcessorLevel", WORD), ("wProcessorRevision", WORD),
    ]


class MEMORYSTATUSEX(Structure):
    _fields_ = [
        ("dwLength", DWORD), ("dwMemoryLoad", DWORD),
        ("ullTotalPhys", c_ulonglong), ("ullAvailPhys", c_ulonglong),
        ("ullTotalPageFile", c_ulonglong), ("ullAvailPageFile", c_ulonglong),
        ("ullTotalVirtual", c_ulonglong), ("ullAvailVirtual", c_ulonglong),
        ("ullAvailExtendedVirtual", c_ulonglong),
    ]


class OSVERSIONINFOW(Structure):
    _fields_ = [
        ("dwOSVersionInfoSize", DWORD), ("dwMajorVersion", DWORD),
        ("dwMinorVersion", DWORD), ("dwBuildNumber", DWORD),
        ("dwPlatformId", DWORD), ("szCSDVersion", c_wchar * 128),
    ]


ARCH = {0: "x86", 5: "ARM", 6: "IA-64", 9: "x64 (AMD64)", 12: "ARM64"}
MEM_TYPE = {20: "DDR", 21: "DDR2", 22: "DDR2 FB-DIMM", 24: "DDR3", 26: "DDR4", 34: "DDR5"}
CHASSIS = {3: "Desktop", 4: "Low Profile Desktop", 6: "Mini Tower", 7: "Tower", 8: "Portable",
           9: "Laptop", 10: "Notebook", 14: "Sub Notebook", 30: "Tablet", 31: "Convertible", 35: "Mini PC"}
CACHE_LEVEL = {3: "L1", 4: "L2", 5: "L3"}
SLOT_USAGE = {3: "вільний", 4: "зайнятий"}


def cpu_load(interval=1.0):
    """Завантаження процесора за інтервал (GetSystemTimes)."""
    def snap():
        i, k, u = FILETIME(), FILETIME(), FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(byref(i), byref(k), byref(u))
        val = lambda x: (x.dwHighDateTime << 32) | x.dwLowDateTime
        return val(i), val(k), val(u)

    a = snap()
    time.sleep(interval)
    b = snap()
    idle = b[0] - a[0]
    total = (b[1] - a[1]) + (b[2] - a[2])  # kernel включає idle
    return 100 * (1 - idle / total) if total else 0.0


# ---------- WMI через PowerShell ----------
def ps_json(cmd):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + cmd + " | ConvertTo-Json -Compress"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        txt = r.stdout.strip()
        if not txt:
            return []
        data = json.loads(txt)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []


def wmi(cls, props, where=None):
    cmd = f"Get-CimInstance {cls}"
    if where:
        cmd += f" -Filter '{where}'"
    cmd += " | Select-Object " + ",".join(props)
    return ps_json(cmd)


# ---------- розділи звіту ----------
def section_os():
    head("Операційна система")
    v = OSVERSIONINFOW()
    v.dwOSVersionInfoSize = sizeof(v)
    ctypes.windll.ntdll.RtlGetVersion(byref(v))
    row("Система", f"{platform.system()} {platform.release()}")
    row("Версія (RtlGetVersion)", f"{v.dwMajorVersion}.{v.dwMinorVersion}, збірка {v.dwBuildNumber}")
    row("Ім'я комп'ютера", socket.gethostname())
    row("Архітектура Python", platform.architecture()[0])


def section_cpu():
    head("Процесор")
    si = SYSTEM_INFO()
    ctypes.windll.kernel32.GetSystemInfo(byref(si))
    row("Архітектура (GetSystemInfo)", ARCH.get(si.wProcessorArchitecture, si.wProcessorArchitecture))
    row("Логічних процесорів", si.dwNumberOfProcessors)
    row("Маска активних процесорів", bin(si.dwActiveProcessorMask))
    row("Розмір сторінки пам'яті", f"{si.dwPageSize} байт")
    row("Гранулярність виділення пам'яті", f"{si.dwAllocationGranularity} байт")
    row("Діапазон адрес застосунку",
        f"{hex(si.lpMinimumApplicationAddress or 0)} - {hex(si.lpMaximumApplicationAddress or 0)}")
    row("Рівень / ревізія", f"{si.wProcessorLevel} / {si.wProcessorRevision}")

    name, freq = platform.processor(), None
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        freq = winreg.QueryValueEx(key, "~MHz")[0]
        row("Виробник (реєстр)", winreg.QueryValueEx(key, "VendorIdentifier")[0])
        row("Ідентифікатор (реєстр)", winreg.QueryValueEx(key, "Identifier")[0])
    except Exception:
        pass
    row("Модель", name)
    if freq:
        row("Тактова частота (реєстр)", f"{freq} МГц")

    for p in wmi("Win32_Processor", ["Name", "NumberOfCores", "NumberOfLogicalProcessors",
                                      "MaxClockSpeed", "SocketDesignation"])[:1]:
        row("Ядер / потоків", f"{p.get('NumberOfCores')} / {p.get('NumberOfLogicalProcessors')}")
        row("Максимальна частота", f"{p.get('MaxClockSpeed')} МГц")
        row("Роз'єм (сокет)", p.get("SocketDesignation"))
        freq = freq or p.get("MaxClockSpeed")
    summary["cpu"] = f"{name}, {freq} МГц" if freq else name

    caches = []
    for c in wmi("Win32_CacheMemory", ["Purpose", "InstalledSize", "Level"]):
        caches.append(f"{CACHE_LEVEL.get(c.get('Level'), '?')} {c.get('InstalledSize')} КБ")
        row("Кеш-пам'ять", f"{CACHE_LEVEL.get(c.get('Level'), '?')}: {c.get('InstalledSize')} КБ ({c.get('Purpose')})")
    summary["cache"] = ", ".join(caches) or "не визначено"

    row("Поточне завантаження ЦП (вимір 1 с)", f"{cpu_load():.1f} %")


def section_memory():
    head("Оперативна пам'ять")
    m = MEMORYSTATUSEX()
    m.dwLength = sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(byref(m))
    row("Всього (GlobalMemoryStatusEx)", gb(m.ullTotalPhys))
    row("Вільно", gb(m.ullAvailPhys))
    row("Завантаження", f"{m.dwMemoryLoad} %")
    row("Віртуальна пам'ять (всього)", gb(m.ullTotalVirtual))

    arr = wmi("Win32_PhysicalMemoryArray", ["MemoryDevices"])
    slots = arr[0].get("MemoryDevices") if arr else None
    mods = wmi("Win32_PhysicalMemory", ["DeviceLocator", "Capacity", "Speed", "SMBIOSMemoryType",
                                         "MemoryType", "Manufacturer"])
    types = set()
    for d in mods:
        t = MEM_TYPE.get(d.get("SMBIOSMemoryType") or d.get("MemoryType"), "тип невідомий")
        types.add(t)
        row(f"Модуль {d.get('DeviceLocator')}", f"{gb(d.get('Capacity'))}, {t}, {d.get('Speed')} МГц, {d.get('Manufacturer')}")
    row("Всього слотів ОП", slots if slots is not None else "невідомо")
    summary["mem"] = f"слотів: {slots}, зайнято: {len(mods)}, тип: {', '.join(types) or 'невідомо'}"


def section_board():
    head("Системна плата, BIOS, чипсет")
    b = wmi("Win32_BaseBoard", ["Manufacturer", "Product"])
    s = wmi("Win32_ComputerSystem", ["Manufacturer", "Model"])
    e = wmi("Win32_SystemEnclosure", ["ChassisTypes"])
    bios = wmi("Win32_BIOS", ["Manufacturer", "SMBIOSBIOSVersion", "ReleaseDate"])
    board = f"{b[0].get('Manufacturer')} {b[0].get('Product')}" if b else "невідомо"
    chassis = "невідомо"
    if e:
        ct = e[0].get("ChassisTypes")
        ct = ct[0] if isinstance(ct, list) and ct else ct
        chassis = CHASSIS.get(ct, f"код {ct}")
    row("Системна плата", board)
    if s:
        row("Комп'ютер", f"{s[0].get('Manufacturer')} {s[0].get('Model')}")
    row("Тип корпусу (форм-фактор системи)", chassis)
    if bios:
        row("BIOS", f"{bios[0].get('Manufacturer')}, версія {bios[0].get('SMBIOSBIOSVersion')}")
    summary["board"] = f"{board}, корпус: {chassis}"

    chip = ps_json("Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "
                   "'Host Bridge|LPC|ISA Bridge|Chipset|PCH|SMBus' } | Select-Object -First 6 Name")
    names = [c.get("Name") for c in chip if c.get("Name")]
    for n in names:
        row("Пристрій чипсету", n)
    summary["chipset"] = "; ".join(names[:3]) or "не визначено (див. модель плати)"


def section_storage():
    head("Накопичувачі")
    items = []
    for d in wmi("Win32_DiskDrive", ["Model", "Size", "InterfaceType", "MediaType"]):
        txt = f"{d.get('Model')}, {gb(d.get('Size'))}, {d.get('InterfaceType')}, {d.get('MediaType')}"
        row("Диск", txt)
        items.append(f"{d.get('Model')} ({gb(d.get('Size'))})")
    for ld in wmi("Win32_LogicalDisk", ["DeviceID", "FileSystem", "DriveType"]):
        try:
            u = shutil.disk_usage(ld["DeviceID"] + "\\")
            row(f"Розділ {ld['DeviceID']}", f"{ld.get('FileSystem')}, всього {gb(u.total)}, вільно {gb(u.free)}")
        except Exception:
            pass
    summary["disk"] = "; ".join(items) or "не визначено"


def section_devices():
    head("Відеоадаптер")
    gpu = []
    for g in wmi("Win32_VideoController", ["Name", "AdapterRAM", "DriverVersion",
                                           "CurrentHorizontalResolution", "CurrentVerticalResolution"]):
        ram = g.get("AdapterRAM")
        ram_txt = gb(ram) if ram and ram > 0 else "невідомо"
        row("Адаптер", f"{g.get('Name')}, пам'ять {ram_txt} (WMI показує не більше 4 ГБ), драйвер {g.get('DriverVersion')}")
        row("Роздільна здатність", f"{g.get('CurrentHorizontalResolution')}x{g.get('CurrentVerticalResolution')}")
        gpu.append(g.get("Name"))
    summary["gpu"] = "; ".join(x for x in gpu if x) or "не визначено"

    head("Звуковий адаптер")
    snd = [s.get("Name") for s in wmi("Win32_SoundDevice", ["Name"]) if s.get("Name")]
    for n in snd:
        row("Пристрій", n)
    summary["sound"] = "; ".join(snd) or "не визначено"

    head("Мережеві адаптери")
    nets = []
    for n in wmi("Win32_NetworkAdapter", ["Name", "MACAddress", "Speed", "NetEnabled"], "PhysicalAdapter=true"):
        try:
            speed = f"{int(n.get('Speed')) // 1_000_000} Мбіт/с"
        except (TypeError, ValueError):
            speed = "швидкість невідома"
        row("Адаптер", f"{n.get('Name')}, MAC {n.get('MACAddress')}, {speed}")
        nets.append(n.get("Name"))
    try:
        row("IP-адреса", socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    summary["net"] = "; ".join(x for x in nets if x) or "не визначено"

    head("Слоти розширення")
    slots = wmi("Win32_SystemSlot", ["SlotDesignation", "CurrentUsage"])
    for s in slots:
        row(s.get("SlotDesignation"), SLOT_USAGE.get(s.get("CurrentUsage"), "невідомо"))
    summary["slots"] = f"{len(slots)} слот(ів)" if slots else "BIOS не повідомляє (типово для ноутбуків)"


def section_table():
    head("Таблиця 2.3. Основні характеристики комп'ютера")
    rows = [
        ("Тип ЦП, частота", "cpu"),
        ("Тип системної плати, форм-фактор", "board"),
        ("Чипсет системної плати", "chipset"),
        ("Тип накопичувача, його ємність", "disk"),
        ("Тип мережевого адаптера", "net"),
        ("Тип відеоадаптера", "gpu"),
        ("Тип звукового адаптера", "sound"),
        ("Роз'єми пам'яті та її тип", "mem"),
        ("Роз'єми розширення системної плати", "slots"),
        ("Обсяг та тип кеш-пам'яті процесора", "cache"),
    ]
    for i, (label, key) in enumerate(rows, 1):
        out(f"  {i:>2}. {label}: {summary.get(key, 'не визначено')}")


def main():
    if sys.platform != "win32":
        print("Ця програма розрахована на Windows.")
        print("Система:", platform.platform(), "| CPU:", platform.processor(), "| ядер:", os.cpu_count())
        return
    out("ЗВІТ ПРО ХАРАКТЕРИСТИКИ КОМП'ЮТЕРА")
    out("(збір даних займає кілька секунд...)")
    for section in (section_os, section_cpu, section_memory, section_board,
                    section_storage, section_devices, section_table):
        section()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_report.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nЗвіт збережено: {path}")


if __name__ == "__main__":
    main()
