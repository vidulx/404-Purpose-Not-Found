
import customtkinter as ctk
from tkinter import messagebox
from pynput import mouse
import sqlite3
import threading
import time
import math
from collections import deque, defaultdict
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

APP_TITLE = "CURSOR EXISTENTIAL ANALYSIS"

UPDATE_INTERVAL = 100
COMMENT_INTERVAL = 5000

PATH_LIMIT = 1800

CLICK_GRID_SIZE = 50
MAX_HEATMAP_CELLS = 150


# ============================================================
# DATABASE
# ============================================================

DB_NAME = "cursor_existential.db"

db = sqlite3.connect(
    DB_NAME,
    check_same_thread=False
)

cursor_db = db.cursor()

cursor_db.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT,
    end_time TEXT,
    total_distance REAL,
    max_speed REAL,
    direction_changes INTEGER,
    reversals INTEGER,
    hesitations INTEGER,
    idle_time REAL,
    movement_count INTEGER
)
""")

cursor_db.execute("""
CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    timestamp TEXT,
    x INTEGER,
    y INTEGER,
    button TEXT
)
""")

db.commit()


# ============================================================
# GLOBAL DATA
# ============================================================

running = True

session_start = datetime.now()

# ---------------- MOVEMENT ----------------

path_points = deque(maxlen=PATH_LIMIT)

last_x = None
last_y = None
last_move_time = None

total_distance = 0.0
current_speed = 0.0
max_speed = 0.0

movement_count = 0
direction_changes = 0
reversals = 0
hesitations = 0
idle_time = 0.0

last_direction = None


# ---------------- CLICKS ----------------

click_points = []

total_clicks = 0
left_clicks = 0
right_clicks = 0
middle_clicks = 0

click_heatmap = defaultdict(int)

click_bucket_positions = defaultdict(list)


# ============================================================
# TTS SETTINGS
# ============================================================

tts_enabled = True

tts_lock = threading.Lock()

last_spoken_comment = ""


# ============================================================
# GUI
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()

app.title(APP_TITLE)

app.geometry("1250x780")

app.minsize(
    1050,
    680
)

screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def distance(x1, y1, x2, y2):

    return math.sqrt(
        (x2 - x1) ** 2 +
        (y2 - y1) ** 2
    )


def direction_from_delta(dx, dy):

    if abs(dx) < 2 and abs(dy) < 2:
        return None

    angle = math.degrees(
        math.atan2(-dy, dx)
    )

    if angle < 0:
        angle += 360

    if 337.5 <= angle or angle < 22.5:
        return "EAST"

    if 22.5 <= angle < 67.5:
        return "NORTHEAST"

    if 67.5 <= angle < 112.5:
        return "NORTH"

    if 112.5 <= angle < 157.5:
        return "NORTHWEST"

    if 157.5 <= angle < 202.5:
        return "WEST"

    if 202.5 <= angle < 247.5:
        return "SOUTHWEST"

    if 247.5 <= angle < 292.5:
        return "SOUTH"

    return "SOUTHEAST"


# ============================================================
# HOTSPOT
# ============================================================

def get_hotspot():

    if not click_heatmap:
        return None

    hottest_bucket = max(
        click_heatmap,
        key=click_heatmap.get
    )

    count = click_heatmap[
        hottest_bucket
    ]

    positions = click_bucket_positions[
        hottest_bucket
    ]

    if positions:

        avg_x = int(
            sum(
                p[0] for p in positions
            ) / len(positions)
        )

        avg_y = int(
            sum(
                p[1] for p in positions
            ) / len(positions)
        )

    else:

        avg_x = (
            hottest_bucket[0] *
            CLICK_GRID_SIZE
        )

        avg_y = (
            hottest_bucket[1] *
            CLICK_GRID_SIZE
        )

    return (
        avg_x,
        avg_y,
        count
    )


# ============================================================
# EXISTENTIAL STATE
# ============================================================

def determine_state():

    if movement_count < 10:
        return "OBSERVING"

    if hesitations > movement_count * 0.25:
        return "HESITANT"

    if reversals > 15:
        return "REGRETFUL"

    if direction_changes > movement_count * 0.45:
        return "CHAOTIC"

    if current_speed > 1200:
        return "DETERMINED"

    if idle_time > 10:
        return "CONTEMPLATIVE"

    return "PURPOSEFUL"


# ============================================================
# EXISTENTIAL COMMENT
# ============================================================

def generate_comment():

    state = determine_state()

    if total_clicks == 0:

        comments = [

            "The cursor has travelled far, yet the subject refuses to commit.",

            "Movement detected. Purpose remains questionable.",

            "The hand moves. The mouse obeys. Nobody knows why.",

            "No clicks detected. Perhaps the subject fears consequences.",

            "The cursor is searching for meaning in a rectangular universe.",

            "Motion continues. Reality provides no explanation.",

            "The subject appears to believe that movement itself is productivity."

        ]

        return comments[
            movement_count %
            len(comments)
        ]

    hotspot = get_hotspot()

    if hotspot:

        hx, hy, hc = hotspot

        comments = [

            f"The subject has clicked {total_clicks} times. {hc} occurred around ({hx}, {hy}). Fascinating.",

            f"A clear preference for ({hx}, {hy}) has emerged. The subject appears emotionally attached to this location.",

            f"{hc} clicks concentrated around ({hx}, {hy}). This is no longer random. This is obsession.",

            "The subject repeatedly clicked one area. Perhaps they believe something will eventually happen.",

            "Click density suggests the subject knows what they are doing. This is concerning.",

            "The cursor moved freely. The clicks, however, developed a favourite location."

        ]

        return comments[
            total_clicks %
            len(comments)
        ]

    return "Clicks have begun. The consequences are irreversible."


# ============================================================
# MOUSE MOVEMENT
# ============================================================

def on_move(x, y):

    global last_x
    global last_y
    global last_move_time

    global total_distance
    global current_speed
    global max_speed

    global movement_count
    global direction_changes
    global reversals
    global hesitations
    global idle_time

    global last_direction

    now = time.time()

    if last_x is not None:

        dx = x - last_x
        dy = y - last_y

        dist = math.sqrt(
            dx * dx +
            dy * dy
        )

        total_distance += dist

        movement_count += 1

        if last_move_time is not None:

            dt = (
                now -
                last_move_time
            )

            if dt > 0:

                current_speed = (
                    dist / dt
                )

                if current_speed > max_speed:

                    max_speed = (
                        current_speed
                    )

                if dt > 0.8:

                    hesitations += 1

                    idle_time += dt

        direction = direction_from_delta(
            dx,
            dy
        )

        if direction and last_direction:

            if direction != last_direction:

                direction_changes += 1

            opposite = {

                "NORTH": "SOUTH",
                "SOUTH": "NORTH",

                "EAST": "WEST",
                "WEST": "EAST",

                "NORTHEAST": "SOUTHWEST",
                "SOUTHWEST": "NORTHEAST",

                "NORTHWEST": "SOUTHEAST",
                "SOUTHEAST": "NORTHWEST"

            }

            if (
                opposite.get(
                    last_direction
                )
                == direction
            ):

                reversals += 1

        if direction:

            last_direction = direction

    last_x = x
    last_y = y

    last_move_time = now

    path_points.append(
        (x, y)
    )


# ============================================================
# MOUSE CLICK
# ============================================================

def on_click(
    x,
    y,
    button,
    pressed
):

    global total_clicks
    global left_clicks
    global right_clicks
    global middle_clicks

    if not pressed:
        return

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )

    button_name = str(
        button
    ).split(".")[-1]

    # Save every click
    click_points.append(
        (
            x,
            y,
            button_name,
            timestamp
        )
    )

    total_clicks += 1

    if button_name == "left":

        left_clicks += 1

    elif button_name == "right":

        right_clicks += 1

    elif button_name == "middle":

        middle_clicks += 1

    # Heatmap bucket
    bucket_x = (
        x //
        CLICK_GRID_SIZE
    )

    bucket_y = (
        y //
        CLICK_GRID_SIZE
    )

    bucket = (
        bucket_x,
        bucket_y
    )

    click_heatmap[
        bucket
    ] += 1

    click_bucket_positions[
        bucket
    ].append(
        (x, y)
    )


# ============================================================
# START MOUSE LISTENER
# ============================================================

listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click
)

listener.start()


# ============================================================
# MAIN FRAME
# ============================================================

main_frame = ctk.CTkFrame(
    app
)

main_frame.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=15
)


# ============================================================
# LEFT FRAME
# ============================================================

left_frame = ctk.CTkFrame(
    main_frame
)

left_frame.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 10)
)


title = ctk.CTkLabel(
    left_frame,
    text="CURSOR EXISTENTIAL ANALYSIS",
    font=(
        "Consolas",
        24,
        "bold"
    )
)

title.pack(
    pady=(15, 5)
)


subtitle = ctk.CTkLabel(
    left_frame,
    text="Every movement is evidence. Every click is a decision.",
    font=(
        "Consolas",
        12
    )
)

subtitle.pack(
    pady=(0, 10)
)


canvas = ctk.CTkCanvas(
    left_frame,
    bg="#090909",
    highlightthickness=1,
    highlightbackground="#333333"
)

canvas.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=10
)


legend = ctk.CTkLabel(
    left_frame,
    text="CLICK HEATMAP:  LOW  →  MEDIUM  →  HIGH  →  EXTREME",
    font=(
        "Consolas",
        10
    )
)

legend.pack(
    pady=(0, 10)
)


# ============================================================
# RIGHT FRAME
# ============================================================

right_frame = ctk.CTkFrame(
    main_frame,
    width=310
)

right_frame.pack(
    side="right",
    fill="y"
)

right_frame.pack_propagate(
    False
)


def stat_label(title_text):

    frame = ctk.CTkFrame(
        right_frame
    )

    frame.pack(
        fill="x",
        padx=10,
        pady=4
    )

    title_label = ctk.CTkLabel(
        frame,
        text=title_text,
        font=(
            "Consolas",
            10
        )
    )

    title_label.pack(
        anchor="w",
        padx=10,
        pady=(5, 0)
    )

    value_label = ctk.CTkLabel(
        frame,
        text="0",
        font=(
            "Consolas",
            16,
            "bold"
        )
    )

    value_label.pack(
        anchor="w",
        padx=10,
        pady=(0, 5)
    )

    return value_label


state_value = stat_label(
    "CURRENT STATE"
)

distance_value = stat_label(
    "TOTAL DISTANCE"
)

speed_value = stat_label(
    "CURRENT SPEED"
)

max_speed_value = stat_label(
    "MAX SPEED"
)

movement_value = stat_label(
    "MOVEMENTS"
)

direction_value = stat_label(
    "DIRECTION CHANGES"
)

reversal_value = stat_label(
    "REVERSALS"
)

hesitation_value = stat_label(
    "HESITATIONS"
)

idle_value = stat_label(
    "IDLE TIME"
)


# ============================================================
# CLICK ANALYSIS
# ============================================================

click_title = ctk.CTkLabel(
    right_frame,
    text="CLICK ANALYSIS",
    font=(
        "Consolas",
        16,
        "bold"
    )
)

click_title.pack(
    pady=(12, 5)
)


click_count_value = stat_label(
    "TOTAL CLICKS"
)

left_click_value = stat_label(
    "LEFT CLICKS"
)

right_click_value = stat_label(
    "RIGHT CLICKS"
)

middle_click_value = stat_label(
    "MIDDLE CLICKS"
)

hotspot_value = stat_label(
    "MOST-CLICKED POSITION"
)

concentration_value = stat_label(
    "CLICK CONCENTRATION"
)


# ============================================================
# EXISTENTIAL COMMENT BOX
# ============================================================

comment_frame = ctk.CTkFrame(
    app
)

comment_frame.pack(
    fill="x",
    padx=15,
    pady=(0, 10)
)


comment_title = ctk.CTkLabel(
    comment_frame,
    text="EXISTENTIAL INTERPRETATION",
    font=(
        "Consolas",
        12,
        "bold"
    )
)

comment_title.pack(
    anchor="w",
    padx=10,
    pady=(8, 0)
)


comment_label = ctk.CTkLabel(
    comment_frame,
    text="Initializing philosophical surveillance...",
    font=(
        "Consolas",
        12
    ),
    wraplength=1100
)

comment_label.pack(
    anchor="w",
    padx=10,
    pady=8
)


# ============================================================
# BUTTON FRAME
# ============================================================

button_frame = ctk.CTkFrame(
    app
)

button_frame.pack(
    fill="x",
    padx=15,
    pady=(0, 15)
)


# ============================================================
# TTS
# ============================================================

def toggle_tts():

    global tts_enabled

    tts_enabled = not tts_enabled

    if tts_enabled:

        tts_button.configure(
            text="🔊 SPEECH: ON"
        )

    else:

        tts_button.configure(
            text="🔇 SPEECH: OFF"
        )


tts_button = ctk.CTkButton(
    button_frame,
    text="🔊 SPEECH: ON",
    command=toggle_tts,
    width=150
)

tts_button.pack(
    side="left",
    padx=5
)


# ============================================================
# CLEAR VISUALIZATION
# ============================================================

visualization_cleared = False


def clear_visualization():

    global visualization_cleared

    canvas.delete(
        "all"
    )

    visualization_cleared = True

    comment_label.configure(
        text="Visual evidence erased. The data remains. Nothing is truly forgotten."
    )


clear_button = ctk.CTkButton(
    button_frame,
    text="🧹 CLEAR VISUAL",
    command=clear_visualization,
    width=150
)

clear_button.pack(
    side="left",
    padx=5
)


# ============================================================
# TTS SPEAK FUNCTION
# ============================================================

def speak(text):

    if not tts_enabled:
        return

    def worker():

        with tts_lock:

            try:

                import pyttsx3

                engine = pyttsx3.init()

                engine.setProperty(
                    "rate",
                    170
                )

                engine.say(
                    text
                )

                engine.runAndWait()

                engine.stop()

            except Exception as e:

                print(
                    "TTS error:",
                    e
                )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


# ============================================================
# DRAW HEATMAP
# ============================================================

def draw_heatmap():

    if not click_heatmap:
        return

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    if (
        canvas_width <= 1
        or canvas_height <= 1
    ):
        return

    max_count = max(
        click_heatmap.values()
    )

    hottest = sorted(
        click_heatmap.items(),
        key=lambda item: item[1],
        reverse=True
    )

    hottest = hottest[
        :MAX_HEATMAP_CELLS
    ]

    for bucket, count in hottest:

        bx, by = bucket

        center_x = (
            (
                bx *
                CLICK_GRID_SIZE
                +
                CLICK_GRID_SIZE / 2
            )
            /
            screen_width
        ) * canvas_width

        center_y = (
            (
                by *
                CLICK_GRID_SIZE
                +
                CLICK_GRID_SIZE / 2
            )
            /
            screen_height
        ) * canvas_height

        intensity = (
            count /
            max_count
        )

        if intensity < 0.25:

            outer_color = "#302000"
            middle_color = "#654000"
            inner_color = "#8B6500"

        elif intensity < 0.50:

            outer_color = "#502000"
            middle_color = "#A04000"
            inner_color = "#D06000"

        elif intensity < 0.75:

            outer_color = "#700000"
            middle_color = "#C02000"
            inner_color = "#FF6500"

        else:

            outer_color = "#800000"
            middle_color = "#FF2000"
            inner_color = "#FFD000"

        radius = (
            18 +
            int(
                25 *
                intensity
            )
        )

        canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill=outer_color,
            outline=""
        )

        radius2 = radius * 0.65

        canvas.create_oval(
            center_x - radius2,
            center_y - radius2,
            center_x + radius2,
            center_y + radius2,
            fill=middle_color,
            outline=""
        )

        radius3 = radius * 0.30

        canvas.create_oval(
            center_x - radius3,
            center_y - radius3,
            center_x + radius3,
            center_y + radius3,
            fill=inner_color,
            outline=""
        )


# ============================================================
# DRAW TRAJECTORY
# ============================================================

def draw_trajectory():

    points = list(
        path_points
    )

    if len(points) < 2:
        return

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    if (
        canvas_width <= 1
        or canvas_height <= 1
    ):
        return

    previous = None

    for x, y in points[-1200:]:

        cx = (
            x /
            screen_width
        ) * canvas_width

        cy = (
            y /
            screen_height
        ) * canvas_height

        if previous:

            px, py = previous

            canvas.create_line(
                px,
                py,
                cx,
                cy,
                fill="#00FFAA",
                width=1
            )

        previous = (
            cx,
            cy
        )


# ============================================================
# DRAW CLICK MARKERS
# ============================================================

def draw_click_markers():

    if not click_points:
        return

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    for (
        x,
        y,
        button_name,
        timestamp
    ) in click_points[-500:]:

        cx = (
            x /
            screen_width
        ) * canvas_width

        cy = (
            y /
            screen_height
        ) * canvas_height

        size = 4

        canvas.create_oval(
            cx - size,
            cy - size,
            cx + size,
            cy + size,
            fill="#FFFFFF",
            outline=""
        )


# ============================================================
# DRAW HOTSPOT
# ============================================================

def draw_hotspot():

    hotspot = get_hotspot()

    if not hotspot:
        return

    x, y, count = hotspot

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    cx = (
        x /
        screen_width
    ) * canvas_width

    cy = (
        y /
        screen_height
    ) * canvas_height

    size = 12

    canvas.create_oval(
        cx - size,
        cy - size,
        cx + size,
        cy + size,
        outline="#FFFFFF",
        width=2
    )

    canvas.create_line(
        cx - 20,
        cy,
        cx + 20,
        cy,
        fill="#FFFFFF",
        width=1
    )

    canvas.create_line(
        cx,
        cy - 20,
        cx,
        cy + 20,
        fill="#FFFFFF",
        width=1
    )

    canvas.create_text(
        cx + 30,
        cy - 20,
        text=(
            f"HOTSPOT\n"
            f"{count} CLICKS"
        ),
        fill="#FFFFFF",
        font=(
            "Consolas",
            9,
            "bold"
        ),
        anchor="w"
    )


# ============================================================
# CANVAS UPDATE
# ============================================================

def update_canvas():

    canvas.delete(
        "all"
    )

    draw_heatmap()

    draw_trajectory()

    draw_click_markers()

    draw_hotspot()

    app.after(
        UPDATE_INTERVAL,
        update_canvas
    )


# ============================================================
# UPDATE STATISTICS
# ============================================================

def update_stats():

    state = determine_state()

    state_value.configure(
        text=state
    )

    distance_value.configure(
        text=f"{total_distance:,.0f} px"
    )

    speed_value.configure(
        text=f"{current_speed:,.0f} px/s"
    )

    max_speed_value.configure(
        text=f"{max_speed:,.0f} px/s"
    )

    movement_value.configure(
        text=f"{movement_count:,}"
    )

    direction_value.configure(
        text=f"{direction_changes:,}"
    )

    reversal_value.configure(
        text=f"{reversals:,}"
    )

    hesitation_value.configure(
        text=f"{hesitations:,}"
    )

    idle_value.configure(
        text=f"{idle_time:.1f} s"
    )


    # ---------------- CLICKS ----------------

    click_count_value.configure(
        text=f"{total_clicks:,}"
    )

    left_click_value.configure(
        text=f"{left_clicks:,}"
    )

    right_click_value.configure(
        text=f"{right_clicks:,}"
    )

    middle_click_value.configure(
        text=f"{middle_clicks:,}"
    )


    hotspot = get_hotspot()

    if hotspot:

        hx, hy, hc = hotspot

        hotspot_value.configure(
            text=(
                f"({hx}, {hy})\n"
                f"{hc} clicks"
            )
        )

        concentration = (
            hc /
            total_clicks
        ) * 100

        concentration_value.configure(
            text=f"{concentration:.1f}%"
        )

    else:

        hotspot_value.configure(
            text="NO CLICKS"
        )

        concentration_value.configure(
            text="0%"
        )

    app.after(
        UPDATE_INTERVAL,
        update_stats
    )


# ============================================================
# COMMENT UPDATE
# ============================================================

def update_comment():

    global last_spoken_comment

    comment = generate_comment()

    comment_label.configure(
        text=comment
    )

    # Only speak if:
    # 1. TTS is enabled
    # 2. Comment changed

    if (
        tts_enabled
        and
        comment != last_spoken_comment
    ):

        last_spoken_comment = comment

        speak(
            comment
        )

    app.after(
        COMMENT_INTERVAL,
        update_comment
    )


# ============================================================
# GENERATE REPORT
# ============================================================

def generate_final_report():

    duration = (
        datetime.now() -
        session_start
    ).total_seconds()

    hotspot = get_hotspot()

    if hotspot:

        hx, hy, hc = hotspot

        hotspot_text = (
            f"({hx}, {hy}) "
            f"with {hc} clicks"
        )

        concentration = (
            hc /
            total_clicks
        ) * 100 if total_clicks else 0

    else:

        hotspot_text = "No clicks"

        concentration = 0


    # Click distribution

    if total_clicks > 0:

        left_percent = (
            left_clicks /
            total_clicks
        ) * 100

        right_percent = (
            right_clicks /
            total_clicks
        ) * 100

        middle_percent = (
            middle_clicks /
            total_clicks
        ) * 100

    else:

        left_percent = 0
        right_percent = 0
        middle_percent = 0


    report = f"""
============================================================
              CURSOR EXISTENTIAL REPORT
============================================================

SESSION START:
{session_start.strftime("%Y-%m-%d %H:%M:%S")}

SESSION END:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

DURATION:
{duration:.1f} seconds


============================================================
                     MOVEMENT
============================================================

TOTAL DISTANCE:
{total_distance:,.2f} pixels

MOVEMENT EVENTS:
{movement_count:,}

CURRENT SPEED:
{current_speed:,.2f} pixels/second

MAX SPEED:
{max_speed:,.2f} pixels/second

DIRECTION CHANGES:
{direction_changes:,}

REVERSALS:
{reversals:,}

HESITATIONS:
{hesitations:,}

IDLE TIME:
{idle_time:.2f} seconds

FINAL STATE:
{determine_state()}


============================================================
                     CLICK ANALYSIS
============================================================

TOTAL CLICKS:
{total_clicks:,}

LEFT CLICKS:
{left_clicks:,}
({left_percent:.1f}%)

RIGHT CLICKS:
{right_clicks:,}
({right_percent:.1f}%)

MIDDLE CLICKS:
{middle_clicks:,}
({middle_percent:.1f}%)

MOST-CLICKED POSITION:
{hotspot_text}

CLICK CONCENTRATION:
{concentration:.2f}%


============================================================
                  CLICK ARCHITECTURE
============================================================

The system recorded every click made during
the observation period.

TOTAL CLICK RECORDS:
{len(click_points):,}

HEATMAP GRID:
{CLICK_GRID_SIZE} x {CLICK_GRID_SIZE} pixels

The hottest region represents the screen area
where the subject demonstrated the greatest
concentration of clicking behaviour.


============================================================
               EXISTENTIAL CONCLUSION
============================================================

The subject moved the cursor approximately
{total_distance:,.0f} pixels.

The subject changed direction
{direction_changes:,} times.

The subject reversed direction
{reversals:,} times.

The subject hesitated
{hesitations:,} times.

The subject clicked
{total_clicks:,} times.

The subject's preferred clicking location was:

{hotspot_text}


FINAL PHILOSOPHICAL STATEMENT:

The cursor moved because the human moved it.

The human moved it because they wanted something.

The click happened because the human believed
something should happen after the click.

Whether anything meaningful actually happened
remains unknown.

The system has recorded the evidence.

Every movement.

Every hesitation.

Every reversal.

Every click.


============================================================
                 END OF ANALYSIS
============================================================
"""

    return report


# ============================================================
# REPORT BUTTON
# ============================================================

def generate_report_button():

    try:

        report = generate_final_report()

        filename = (
            "cursor_existential_report_"
            +
            datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            +
            ".txt"
        )

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                report
            )


        # Create report window

        report_window = ctk.CTkToplevel(
            app
        )

        report_window.title(
            "Existential Analysis Report"
        )

        report_window.geometry(
            "850x650"
        )

        report_window.grab_set()


        report_text = ctk.CTkTextbox(
            report_window,
            font=(
                "Consolas",
                11
            )
        )

        report_text.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        report_text.insert(
            "1.0",
            report
        )

        report_text.configure(
            state="disabled"
        )


        bottom = ctk.CTkFrame(
            report_window
        )

        bottom.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )


        saved_label = ctk.CTkLabel(
            bottom,
            text=(
                f"Saved as: {filename}"
            ),
            font=(
                "Consolas",
                10
            )
        )

        saved_label.pack(
            side="left",
            padx=10
        )


        close_button = ctk.CTkButton(
            bottom,
            text="CLOSE",
            command=report_window.destroy,
            width=120
        )

        close_button.pack(
            side="right",
            padx=5
        )


        print(report)

        print(
            f"\nReport saved as: {filename}"
        )


    except Exception as e:

        messagebox.showerror(
            "Report Error",
            f"Could not generate report:\n\n{e}"
        )


report_button = ctk.CTkButton(
    button_frame,
    text="📄 GENERATE REPORT",
    command=generate_report_button,
    width=170
)

report_button.pack(
    side="left",
    padx=5
)


# ============================================================
# SAVE SESSION TO DATABASE
# ============================================================

def save_session():

    try:

        end_time = datetime.now()

        cursor_db.execute("""
        INSERT INTO sessions (
            start_time,
            end_time,
            total_distance,
            max_speed,
            direction_changes,
            reversals,
            hesitations,
            idle_time,
            movement_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            session_start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            end_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            total_distance,

            max_speed,

            direction_changes,

            reversals,

            hesitations,

            idle_time,

            movement_count

        ))

        session_id = (
            cursor_db.lastrowid
        )


        # Save EVERY click

        for (
            x,
            y,
            button_name,
            timestamp
        ) in click_points:

            cursor_db.execute("""
            INSERT INTO clicks (
                session_id,
                timestamp,
                x,
                y,
                button
            )
            VALUES (?, ?, ?, ?, ?)
            """, (

                session_id,

                timestamp,

                x,

                y,

                button_name

            ))


        db.commit()

        return session_id


    except Exception as e:

        print(
            "Database error:",
            e
        )

        return None


# ============================================================
# CLOSE APPLICATION
# ============================================================

def close_app():

    global running

    answer = messagebox.askyesno(
        "End Analysis",
        "End the cursor analysis session?"
    )

    if not answer:
        return


    running = False


    try:

        listener.stop()

    except Exception:
        pass


    # Save session

    session_id = save_session()


    # Save final report automatically

    try:

        report = (
            generate_final_report()
        )

        filename = (
            "cursor_existential_report_"
            +
            datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            +
            ".txt"
        )

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                report
            )

        print(
            f"Final report saved as: {filename}"
        )

    except Exception as e:

        print(
            "Could not save final report:",
            e
        )


    try:

        db.close()

    except Exception:
        pass


    app.destroy()


app.protocol(
    "WM_DELETE_WINDOW",
    close_app
)


# ============================================================
# START APPLICATION
# ============================================================

update_canvas()

update_stats()

update_comment()

app.mainloop()
