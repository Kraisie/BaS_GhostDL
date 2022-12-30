import os
from uuid import UUID
from xml.etree import ElementTree as ET
from requests import get
from prettytable import PrettyTable

temp_path = os.getenv("LOCALAPPDATA") + "/Temp/.net/BotsAreStupid"
leaderboard_url = "http://bas.leleg.de/game/Preview/Scores/List.php"
run_data_url = "http://bas.leleg.de/game/Preview/Scores/Get.php?id="
sim_modes = ["default, nojump", "lowgrav", "hook360", "elastichook", "boostedboosters", "legacy"]

leaderboard_entry_limit = 10
keep_comments = False
keep_blank_lines = False
sort_by = "minSpeed"
sim_mode = "default"


def find_levels_dir():
    children = [child for child in os.listdir(temp_path) if os.path.isdir(temp_path + "/" + child)]
    for child in children:
        lvl_path = temp_path + "/" + child + "/Content/Levels"
        if not os.path.isdir(lvl_path):
            continue

        return lvl_path

    raise FileNotFoundError("Could not find level directory!")


def is_valid_uuid(file_name):
    try:
        UUID(file_name)
        return True
    except ValueError:
        return False


def find_level_files(path):
    levels = []
    for child in os.listdir(path):
        if not os.path.isfile(path + "/" + child):
            continue

        if not child.endswith(".xml"):
            continue

        if not is_valid_uuid(child.removesuffix(".xml")):
            continue

        levels.append(path + "/" + child)

    return levels


def build_level_list(lvl_files):
    levels = []
    for file in lvl_files:
        root = ET.parse(file).getroot()
        meta = root[0]
        if meta[1].text == "Editor":  # ignore the base level editor level
            continue

        levels.append({'id': meta[0].text, 'name': meta[1].text})

    return sorted(levels, key=lambda k: k['name'])


def find_levels():
    try:
        lvl_path = find_levels_dir()
        lvl_files = find_level_files(lvl_path)
        return build_level_list(lvl_files)
    except FileNotFoundError:
        raise


def settings_config():
    print("You can configure some (4) settings now. Type skip at any point to skip the rest of the configuration.")
    answer = input("Do you want to order the leaderboards by min lines? (default: min time) [y/n]: ")
    if answer.lower() == "skip":
        return

    if answer.lower()[0] == 'y':
        global sort_by
        sort_by = "minLines"

    answer = input("How many entries do you want to see on the leaderboard? (default: 10) [1-50]: ")
    if answer.lower() == "skip":
        return

    if answer.isdigit():
        entries = int(answer)
        if 0 < entries <= 50:
            global leaderboard_entry_limit
            leaderboard_entry_limit = entries

    answer = input(f"Select one of the following modes (case-sensitive, enter anything to select default): ({', '.join(sim_modes)}): ")
    if answer.lower() == "skip":
        return

    if answer in sim_modes:
        global sim_mode
        sim_mode = answer

    answer = input("Do you want to see comments in the code that were written by the player? (default: no) [y/n]: ")
    if answer.lower() == "skip":
        return

    if answer.lower()[0] == 'y':
        global keep_comments
        keep_comments = True

    answer = input("Do you want to keep blank lines in the code that were used by the player? (default: no) [y/n]: ")
    if answer.lower() == "skip":
        return

    if answer.lower()[0] == 'y':
        global keep_blank_lines
        keep_blank_lines = True


def show_levels(levels):
    lvl_table = PrettyTable(['ID', 'Level Name'])
    for index, level in enumerate(levels, start=1):
        lvl_table.add_row([index, level['name']])

    print(lvl_table)


def get_level_selection(levels):
    while True:
        str_index = input("\nType the number of the level: ")
        if not str_index.isdigit():
            print("Invalid input! Please only use the number of the level you want to select.")
            continue

        index = int(str_index)
        if index <= 0 or index > len(levels):
            print("That level does not exist! Please use a valid number.")
            continue

        return levels[index - 1]


def request_data(url, query):
    request = get(url, params=query)
    return request.text


# leaderboard structure:
# Time | Lines | Player Name | Run ID | ??? | timestamp
def parse_leaderboard_data(data):
    leaderboard = []
    lines = data.split('*')
    for line in lines:
        cols = line.split('%')
        run = {'time': cols[0], 'lines': cols[1], 'player': cols[2], 'id': cols[3], '?': cols[4], 'timestamp': cols[5]}
        leaderboard.append(run)

    return leaderboard


def get_leaderboard(level):
    query = {'search': sort_by, 'levelid': level['id']}
    data = request_data(leaderboard_url, query)
    return parse_leaderboard_data(data)


def show_leaderboard(data):
    leaderboard = PrettyTable(['ID', 'Time (ms)', 'Lines', 'Player Name'])
    for index, run in enumerate(data[:leaderboard_entry_limit], start=1):
        leaderboard.add_row([index, run['time'], run['lines'], run['player']])

    print(leaderboard)


def get_run_selection(leaderboard):
    while True:
        str_index = input("\nType the number of the ghost you want to see: ")
        if not str_index.isdigit():
            print("Invalid input! Please only use the number of the ghost you want to select.")
            continue

        index = int(str_index)
        if index <= 0 or index > leaderboard_entry_limit:
            print("That ghost does not exist! Please use a valid number.")
            continue

        return leaderboard[index - 1]


# code structure:
# | -> newline
# // -> comment
# here we trust the game data to not include | anywhere (especially in comments) as we can not type that in the game
# however, if there is no serverside verification this might break when users POST code with | to the server manually
def parse_code_data(data):
    code_lines = []
    lines = data.split('|')
    for line in lines:
        if not keep_comments and line.startswith('//'):
            continue

        if not keep_blank_lines and not line.strip():  # line.strip() -> false if line blank
            continue

        code_lines.append(line)

    return code_lines


def get_code(run):
    query = {'id': run['id']}
    data = request_data(run_data_url, query)
    return parse_code_data(data)


def show_code(code):
    numerated_code = PrettyTable(align='l')
    numerated_code.border = False
    numerated_code.preserve_internal_border = True
    numerated_code.header = False
    for line_no, line in enumerate(code, start=1):
        numerated_code.add_row([line_no, line])

    print(numerated_code)


def do_level_code_request(levels):
    show_levels(levels)
    level = get_level_selection(levels)
    leaderboard = get_leaderboard(level)
    show_leaderboard(leaderboard)
    run = get_run_selection(leaderboard)
    ghost_code = get_code(run)
    show_code(ghost_code)


def wants_to_exit():
    answer = input("\nType exit to stop the program. Type anything else to continue with another level: ")
    if not answer or answer.lower() != 'exit':
        return False

    return True


def main():
    try:
        levels = find_levels()
    except FileNotFoundError as e:
        print(getattr(e, 'message', repr(e)))
        return

    if len(levels) == 0:
        print("Could not find any levels!")
        return

    settings_config()
    while True:
        do_level_code_request(levels)
        if wants_to_exit():
            break


if __name__ == "__main__":
    main()
