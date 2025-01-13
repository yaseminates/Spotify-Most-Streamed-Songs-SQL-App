

# --- --- --- PREPARATION --- --- ---
from rich.progress import Progress
import time

#for fun... this is a "loading screen" for when the program is shut
def loading():
    with Progress() as progress:
        task = progress.add_task("[green]Exiting the Program...", total=25)
        for _ in range(25):
            time.sleep(0.05)  # Simulate processing delay
            progress.update(task, advance=1)


import mysql.connector
import pandas as pd
from IPython.display import display # we don't use this in the final version
from rich.console import Console
from rich.table import Table
from rich import print
from rich.progress import Progress
import getpass

username = None # change to your own username, or don't theres more than enough error handling...
password = None #change to your own password
host = None #change host if needed 
filepath = None

# MySQL connection details
config = {
    "user": username,          
    "password": password,  
    "host": host
}

# Connect to MySQL (used later)
def connect_db():
    return mysql.connector.connect(**config) # used unpacking

# Drop the database (used later)
def drop_database(cursor, db_name):
    try:
        # Drop the database if it exists
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        #print(f"Database {db_name} dropped successfully.") #used in early stages
    except mysql.connector.Error as err:
        print(f"Error: {err}")

# Create the database if it doesn't exist (used later)
def create_database(cursor):
    cursor.execute("CREATE DATABASE IF NOT EXISTS spotify_db")
    cursor.execute("USE spotify_db")

def runProgram():
    try:
        create_database(cursor)
        #print("Database created successfully.") # used in the early stages to check

        create_tables(cursor)
        conn.commit()

        populate_tables(cursor)
        conn.commit()
        #print("Tables created and populated successfully.")  # also used in the early stages to check
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")


# --- --- --- CREATE THE TABLES --- --- ---


# Create tables based on the ER diagram with relationship tables for ease of calulationg
def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Platform (
        platform_id INT AUTO_INCREMENT PRIMARY KEY,
        platform_name VARCHAR(50) UNIQUE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Artist (
        artist_id INT AUTO_INCREMENT PRIMARY KEY,
        artist_name VARCHAR(255) UNIQUE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Track (
        track_id INT AUTO_INCREMENT PRIMARY KEY,
        track_name VARCHAR(255) NOT NULL,
        release_year INT,
        release_month INT,
        release_day INT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS MusicalAttributes (
        music_id INT AUTO_INCREMENT PRIMARY KEY,
        bpm FLOAT,
        key_signature VARCHAR(10),
        mode VARCHAR(10),
        danceability FLOAT,
        valence FLOAT,
        energy FLOAT,
        acousticness FLOAT,
        instrumentalness FLOAT,
        liveness FLOAT,
        speechiness FLOAT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TrackMusicalAttributes (
        track_id INT,
        music_id INT,
        PRIMARY KEY (track_id, music_id),
        FOREIGN KEY (track_id) REFERENCES Track(track_id),
        FOREIGN KEY (music_id) REFERENCES MusicalAttributes(music_id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS StreamingMetric (
        platform_id INT,
        track_id INT,
        metric_type ENUM('in_playlists', 'in_charts', 'streams'),
        metric_value BIGINT,
        PRIMARY KEY (platform_id, track_id, metric_type),
        FOREIGN KEY (platform_id) REFERENCES Platform(platform_id),
        FOREIGN KEY (track_id) REFERENCES Track(track_id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TrackArtist (
        track_id INT,
        artist_id INT,
        PRIMARY KEY (track_id, artist_id),
        FOREIGN KEY (track_id) REFERENCES Track(track_id),
        FOREIGN KEY (artist_id) REFERENCES Artist(artist_id)
    );
    """)# Artist-Track relationship


# --- --- --- POPULATE THE TABLES --- --- ---


# function to populate ALL tables
def populate_tables(cursor):
    
    # populate the Platforms Table
    platforms = ["Spotify", "Shazam", "Deezer", "Apple"]
    for platform in platforms:
        cursor.execute("INSERT IGNORE INTO Platform (platform_name) VALUES (%s)", (platform,))

    # try reading the CSV file with different encodings
    try:
        spotify_df = pd.read_csv(filepath, encoding='utf-8')
        spotify_df = spotify_df.replace({r'[^\x00-\x7F]+': '?'}, regex=True)
    except UnicodeDecodeError:
        spotify_df = pd.read_csv(filepath, encoding='cp1252')

    # populate the Artist table
    for artists in spotify_df['artist(s)_name']:

        # Split multiple artists (e.g., "Latto, Jung Kook") by comma and strip any whitespace
        individual_artists = [artist.strip() for artist in artists.split(',')]  

        # insert each UNIQUE artist into the Artist table
        for artist in individual_artists:
            artist = artist.strip()  # remove unnecessary spaces
            if artist:  # skip empty entires
                cursor.execute("INSERT IGNORE INTO Artist (artist_name) VALUES (%s)", (artist,))

    # populate the Track table
    for _, row in spotify_df.iterrows():

        cursor.execute("""
            INSERT INTO Track (track_name, release_year, release_month, release_day)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE track_name = track_name
        """, (row['track_name'], row['released_year'], row['released_month'], row['released_day']))
        
        # get the track ID 
        cursor.execute("SELECT LAST_INSERT_ID()")
        track_id = cursor.fetchone()[0]

        # replace NaN values with None (NULL)
        bpm = row['bpm'] if pd.notna(row['bpm']) else None
        key_signature = row['key'] if pd.notna(row['key']) else None
        mode = row['mode'] if pd.notna(row['mode']) else None
        danceability = row['danceability_%'] if pd.notna(row['danceability_%']) else None
        valence = row['valence_%'] if pd.notna(row['valence_%']) else None
        energy = row['energy_%'] if pd.notna(row['energy_%']) else None
        acousticness = row['acousticness_%'] if pd.notna(row['acousticness_%']) else None
        instrumentalness = row['instrumentalness_%'] if pd.notna(row['instrumentalness_%']) else None
        liveness = row['liveness_%'] if pd.notna(row['liveness_%']) else None
        speechiness = row['speechiness_%'] if pd.notna(row['speechiness_%']) else None

        # populate the MusicalAttributes table
        cursor.execute("""
            INSERT INTO MusicalAttributes (bpm, key_signature, mode, danceability, valence, energy, acousticness, instrumentalness, liveness, speechiness)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE music_id = music_id
        """, (bpm, key_signature, mode, danceability, valence, energy, acousticness, instrumentalness, liveness, speechiness))

        # get the music_id of the row
        cursor.execute("SELECT LAST_INSERT_ID()")
        music_id = cursor.fetchone()[0]

        # the relationship between Track and its MusicalAttributes
        cursor.execute("""
            INSERT INTO TrackMusicalAttributes (track_id, music_id)
            VALUES (%s, %s)
        """, (track_id, music_id))

        # the relationship between Track and its Artist
        individual_artists = [artist.strip() for artist in row['artist(s)_name'].split(',')]  # can handle multiple artists
        
        for artist in individual_artists:
            # check if artist already exists
            cursor.execute("SELECT artist_id FROM Artist WHERE artist_name = %s", (artist,))
            artist_id = cursor.fetchone()

            if artist_id:
                artist_id = artist_id[0]  # extract artist_id

                # insert into TrackArtist 
                cursor.execute("""
                    INSERT IGNORE INTO TrackArtist (track_id, artist_id)
                    VALUES (%s, %s)
                """, (track_id, artist_id))

        
         # populate the StreamingMetric table for each platform and metric type
        platforms_data = {
            "Spotify": {
                "in_playlists": row['in_spotify_playlists'],
                "in_charts": row['in_spotify_charts'],
                "streams": row['streams']
            }, # Spotify is the only platform with the streams value...
            "Apple": {
                "in_playlists": row['in_apple_playlists'],
                "in_charts": row['in_apple_charts']
            }, 
            "Deezer": {
                "in_playlists": row['in_deezer_playlists'],
                "in_charts": row['in_deezer_charts']
            },
            "Shazam": {
                "in_charts": row['in_shazam_charts']
            } # Shazam is not a streaming service and does not offer playlists...
        }

        for platform, metrics in platforms_data.items():
            cursor.execute("SELECT platform_id FROM Platform WHERE platform_name = %s", (platform,))
            platform_id = cursor.fetchone()[0]

            # Split metrics string into individual metric-value pairs if necessary                                              #-----------------------
            if isinstance(metrics, str):
                metrics = dict(item.split(":") for item in metrics.split() if ":" in item)

            for metric_type, metric_value in metrics.items():

                # we remove the commas, as some values exist where they're "4,567" instead of  the desired 4567 

                # remove commas and convert to integer, default to 0 
                try:
                    metric_value = int(str(metric_value).replace(",", ""))
                except ValueError:
                    metric_value = 0  # default if conversion fails

                # handle each metric type separately
                cursor.execute("""
                    INSERT IGNORE INTO StreamingMetric (platform_id, track_id, metric_type, metric_value)
                    VALUES (%s, %s, %s, %s)
                """, (platform_id, track_id, metric_type, metric_value))


# --- --- --- see the comments below for more code used though the early stages for "checks" and "validation" --- --- ---


# --- --- --- QUERIES --- --- ---


query1 = """
        SELECT 
            CASE
                WHEN T.release_month IN (12, 1, 2) THEN 'Winter'
                WHEN T.release_month IN (3, 4, 5) THEN 'Spring'
                WHEN T.release_month IN (6, 7, 8) THEN 'Summer'
                WHEN T.release_month IN (9, 10, 11) THEN 'Fall'
            END AS season,
            ROUND(AVG(MA.bpm), 4),
            ROUND(SUM(CASE WHEN MA.mode = 'Major' THEN 1 ELSE 0 END) / COUNT(*) * 100) AS percent_major,
            ROUND(SUM(CASE WHEN MA.mode = 'Minor' THEN 1 ELSE 0 END) / COUNT(*) * 100) AS percent_minor,
            ROUND(AVG(MA.valence)) AS avg_valence,
            ROUND(AVG(MA.energy)) AS avg_energy,
            ROUND(AVG(MA.danceability)) AS avg_danceability,
            ROUND(AVG(MA.acousticness)) AS avg_acousticness,
            ROUND(AVG(MA.liveness)) AS avg_liveness,
            ROUND(AVG(MA.speechiness)) AS avg_speechiness
        FROM Track T
        JOIN TrackMusicalAttributes TMA ON T.track_id = TMA.track_id
        JOIN MusicalAttributes MA ON TMA.music_id = MA.music_id
        GROUP BY season
        ORDER BY FIELD(season, 'Winter', 'Spring', 'Summer', 'Fall');
"""

query2 = """
        WITH MetricStats AS (
            SELECT 
                P.platform_name,
                AVG(CASE WHEN SM.metric_type = 'in_playlists' THEN SM.metric_value END) AS avg_playlists,
                STDDEV(CASE WHEN SM.metric_type = 'in_playlists' THEN SM.metric_value END) AS stddev_playlists,

                AVG(CASE WHEN SM.metric_type = 'in_charts' THEN 1.0 / SM.metric_value END) AS avg_inverted_chart_rank,
                STDDEV(CASE WHEN SM.metric_type = 'in_charts' THEN 1.0 / SM.metric_value END) AS stddev_inverted_chart_rank,

                AVG(CASE WHEN P.platform_name = 'Spotify' AND SM.metric_type = 'streams' THEN SM.metric_value END) AS avg_spotify_streams,
                STDDEV(CASE WHEN P.platform_name = 'Spotify' AND SM.metric_type = 'streams' THEN SM.metric_value END) AS stddev_spotify_streams
            FROM StreamingMetric SM
            JOIN Platform P ON SM.platform_id = P.platform_id
            GROUP BY P.platform_name
        )

        SELECT 
            A.artist_name,
            -- Weighted playlist counts normalized by standard deviation
            ROUND(SUM(CASE WHEN P.platform_name = 'Spotify' AND SM.metric_type = 'in_playlists' 
                    THEN (SM.metric_value / (SELECT avg_playlists FROM MetricStats WHERE platform_name = 'Spotify')) 
                        * (1 / (SELECT stddev_playlists FROM MetricStats WHERE platform_name = 'Spotify')) ELSE 0 END) +
            SUM(CASE WHEN P.platform_name = 'Apple' AND SM.metric_type = 'in_playlists' 
                    THEN (SM.metric_value / (SELECT avg_playlists FROM MetricStats WHERE platform_name = 'Apple')) 
                        * (1 / (SELECT stddev_playlists FROM MetricStats WHERE platform_name = 'Apple')) ELSE 0 END) +
            SUM(CASE WHEN P.platform_name = 'Deezer' AND SM.metric_type = 'in_playlists' 
                    THEN (SM.metric_value / (SELECT avg_playlists FROM MetricStats WHERE platform_name = 'Deezer')) 
                        * (1 / (SELECT stddev_playlists FROM MetricStats WHERE platform_name = 'Deezer')) ELSE 0 END) +
            SUM(CASE WHEN P.platform_name = 'Shazam' AND SM.metric_type = 'in_playlists' 
                    THEN (SM.metric_value / (SELECT avg_playlists FROM MetricStats WHERE platform_name = 'Shazam')) 
                        * (1 / (SELECT stddev_playlists FROM MetricStats WHERE platform_name = 'Shazam')) ELSE 0 END) 
            +

            -- Weighted inverted chart ranks normalized by standard deviation
            SUM(CASE WHEN P.platform_name = 'Spotify' AND SM.metric_type = 'in_charts' 
                    THEN ((1.0 / SM.metric_value) / (SELECT avg_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Spotify')) 
                        * (1 / (SELECT stddev_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Spotify')) ELSE 0 END) +
            SUM(CASE WHEN P.platform_name = 'Apple' AND SM.metric_type = 'in_charts' 
                    THEN ((1.0 / SM.metric_value) / (SELECT avg_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Apple')) 
                        * (1 / (SELECT stddev_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Apple')) ELSE 0 END) +
            SUM(CASE WHEN P.platform_name = 'Deezer' AND SM.metric_type = 'in_charts' 
                    THEN ((1.0 / SM.metric_value) / (SELECT avg_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Deezer')) 
                        * (1 / (SELECT stddev_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Deezer')) ELSE 0 END) +
            SUM(CASE WHEN P.platform_name = 'Shazam' AND SM.metric_type = 'in_charts' 
                    THEN ((1.0 / SM.metric_value) / (SELECT avg_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Shazam')) 
                        * (1 / (SELECT stddev_inverted_chart_rank FROM MetricStats WHERE platform_name = 'Shazam')) ELSE 0 END) 
            +

            -- Weighted streams for Spotify normalized by standard deviation
            SUM(CASE WHEN P.platform_name = 'Spotify' AND SM.metric_type = 'streams' 
                    THEN (SM.metric_value / (SELECT avg_spotify_streams FROM MetricStats WHERE platform_name = 'Spotify')) 
                        * (1 / (SELECT stddev_spotify_streams FROM MetricStats WHERE platform_name = 'Spotify')) ELSE 0 END), 2) AS weighted_score
        FROM Track T
        JOIN StreamingMetric SM ON T.track_id = SM.track_id
        JOIN Platform P ON SM.platform_id = P.platform_id
        JOIN TrackArtist TA ON T.track_id = TA.track_id
        JOIN Artist A ON TA.artist_id = A.artist_id
        GROUP BY A.artist_name
        ORDER BY weighted_score DESC
        LIMIT 10;
"""

query3 = """
        WITH DanceabilityStats AS (
            SELECT 
                CASE
                    WHEN MA.danceability BETWEEN 0 AND 30 THEN '0-30%'
                    WHEN MA.danceability BETWEEN 31 AND 50 THEN '31-50%'
                    WHEN MA.danceability BETWEEN 51 AND 60 THEN '51-60%'
                    WHEN MA.danceability BETWEEN 61 AND 80 THEN '61-80%'
                    ELSE '81-100%'
                END AS danceability_range,
                ROUND(AVG(SM.metric_value)) AS avg_playlists,
                CAST(ROUND(STDDEV(SM.metric_value))AS SIGNED) AS stddev_playlists
            FROM MusicalAttributes MA
            JOIN TrackMusicalAttributes TMA ON MA.music_id = TMA.music_id
            JOIN StreamingMetric SM ON TMA.track_id = SM.track_id
            JOIN Platform P ON SM.platform_id = P.platform_id
            WHERE SM.platform_id = 1 AND SM.metric_type = 'in_playlists'
            GROUP BY danceability_range
        )

        SELECT 
            T.track_name,  -- Get the track name from the Track table
            MA.danceability AS danceability_percentage,
            CASE
                WHEN MA.danceability BETWEEN 0 AND 30 THEN '0-30%'
                WHEN MA.danceability BETWEEN 31 AND 50 THEN '31-50%'
                WHEN MA.danceability BETWEEN 51 AND 60 THEN '51-60%'
                WHEN MA.danceability BETWEEN 61 AND 80 THEN '61-80%'
                ELSE '81-100%'
            END AS danceability_range,
            ROUND(SM.metric_value, 2) AS actual_playlists,
            ds.avg_playlists,
            ds.stddev_playlists,
            ROUND((SM.metric_value - ds.avg_playlists) / ds.stddev_playlists, 2) AS deviation
        FROM MusicalAttributes MA
        JOIN TrackMusicalAttributes TMA ON MA.music_id = TMA.music_id
        JOIN StreamingMetric SM ON TMA.track_id = SM.track_id
        JOIN DanceabilityStats ds ON 
            CASE
                WHEN MA.danceability BETWEEN 0 AND 30 THEN '0-30%'
                WHEN MA.danceability BETWEEN 31 AND 50 THEN '31-50%'
                WHEN MA.danceability BETWEEN 51 AND 70 THEN '51-60%'
                WHEN MA.danceability BETWEEN 71 AND 90 THEN '61-80%'
                ELSE '81-100%'
            END = ds.danceability_range
        JOIN Track T ON TMA.track_id = T.track_id  -- Join to get track name
        WHERE SM.platform_id = 1 AND SM.metric_type = 'in_playlists'
        AND ABS((SM.metric_value - ds.avg_playlists) / ds.stddev_playlists) > 2.5  -- Flagging significant deviations
        ORDER BY deviation DESC;
"""

query4 = """
        SELECT 
            T.track_name, 
            GROUP_CONCAT(a.artist_name SEPARATOR ', ') AS artists,
            MA.bpm
        FROM 
            Track T
        JOIN 
             TrackArtist ta ON t.track_id = ta.track_id
        JOIN 
            Artist a ON ta.artist_id = a.artist_id
        JOIN 
            TrackMusicalAttributes TMA ON T.track_id = TMA.track_id
        JOIN 
            MusicalAttributes MA ON TMA.music_id = MA.music_id
        WHERE 
            MA.valence > 50 -- High valence threshold (scaled to 100)
            AND MA.bpm > 130 -- Tempo above 130 BPM
            AND MA.energy > 70 -- High energy threshold (scaled to 100)
            AND MA.danceability > 60 -- Rhythmic suitability threshold (scaled to 100)
            AND MA.acousticness < 30 -- Synthetic/electronic tracks (scaled to 100)
            AND MA.speechiness < 33 -- Minimize spoken words (scaled to 100)
            AND MA.liveness < 50 -- Avoid live recordings (scaled to 100)
        GROUP BY 
            t.track_id, MA.bpm, MA.valence, MA.energy, MA.danceability
        ORDER BY 
            MA.bpm ASC, -- Sort by BPM (lowest first)
            MA.valence DESC, -- Sort by valence (highest first)
            MA.energy DESC, -- Sort by energy (highest first)
            MA.danceability ASC -- Sort by danceability (highest first)
            
        LIMIT 40;
"""

query5 = """
        SELECT 
            t.track_name, 
            GROUP_CONCAT(a.artist_name SEPARATOR ', ') AS artists,  
            ma.key_signature AS 'key',
            ma.mode, 
            MIN(sm1.metric_value) AS spotify_rank, 
            MIN(sm2.metric_value) AS apple_rank, 
            MIN(sm3.metric_value) AS deezer_rank
        FROM Track t
        JOIN TrackArtist ta ON t.track_id = ta.track_id
        JOIN Artist a ON ta.artist_id = a.artist_id
        JOIN TrackMusicalAttributes tma ON t.track_id = tma.track_id
        JOIN MusicalAttributes ma ON tma.music_id = ma.music_id
        JOIN StreamingMetric sm1 ON t.track_id = sm1.track_id AND sm1.platform_id = 1 AND sm1.metric_type = 'in_charts'
        JOIN StreamingMetric sm2 ON t.track_id = sm2.track_id AND sm2.platform_id = 2 AND sm2.metric_type = 'in_charts'
        JOIN StreamingMetric sm3 ON t.track_id = sm3.track_id AND sm3.platform_id = 3 AND sm3.metric_type = 'in_charts'
        WHERE sm1.metric_value <= 10 AND sm1.metric_value >= 1
        AND sm2.metric_value <= 10 AND sm2.metric_value >= 1
        AND sm3.metric_value <= 10 AND sm3.metric_value >= 1
        GROUP BY t.track_id, ma.key_signature, ma.mode -- Group by track-specific fields only
        ORDER BY spotify_rank, apple_rank, deezer_rank;
"""

query6 = """
        SELECT 
            t.track_name, 
            GROUP_CONCAT(a.artist_name SEPARATOR ', ') AS artists,  
            ma.energy AS energy_percent, 
            ma.speechiness AS speechiness_percent, 
            sm.metric_value AS spotify_chart_rank
        FROM Track t
        JOIN TrackArtist ta ON t.track_id = ta.track_id
        JOIN Artist a ON ta.artist_id = a.artist_id
        JOIN TrackMusicalAttributes tma ON t.track_id = tma.track_id
        JOIN MusicalAttributes ma ON tma.music_id = ma.music_id
        JOIN StreamingMetric sm ON t.track_id = sm.track_id
        WHERE sm.platform_id = 1 -- Spotify
        AND sm.metric_type = 'in_charts'
        AND ma.energy > 70
        AND ma.speechiness < 10
        AND sm.metric_value <= 20 AND sm.metric_value >= 1
        GROUP BY t.track_id, ma.energy, ma.speechiness, sm.metric_value -- Group by track to avoid duplicates
        ORDER BY ma.energy DESC, sm.metric_value ASC
        LIMIT 10;
"""

query7 = """
                SELECT DISTINCT
                    t.track_name, 
                    GROUP_CONCAT(DISTINCT a.artist_name ORDER BY a.artist_name SEPARATOR ', ') AS artist_names, 
                    ma.danceability, 
                    ma.valence, 
                    sm.metric_value AS spotify_rank
                FROM Track t
                JOIN TrackArtist ta ON t.track_id = ta.track_id
                JOIN Artist a ON ta.artist_id = a.artist_id
                JOIN TrackMusicalAttributes tma ON t.track_id = tma.track_id
                JOIN MusicalAttributes ma ON tma.music_id = ma.music_id
                JOIN StreamingMetric sm ON t.track_id = sm.track_id
                JOIN Platform p ON sm.platform_id = p.platform_id
                WHERE 
                    p.platform_name = 'Spotify' 
                    AND sm.metric_type = 'in_charts' 
                    AND sm.metric_value <= 25 AND sm.metric_value >= 1
                    AND ma.danceability > 80 
                    AND ma.valence > 80
                GROUP BY 
                    t.track_id, t.track_name, ma.danceability, ma.valence, sm.metric_value
                ORDER BY 
                    ma.danceability DESC, 
                    ma.valence DESC
                LIMIT 10;
"""


# --- --- --- QUERY 8, CUSTOM SONG RECOMMENDATION --- --- ---

def get_user_preferences():
    print("""
            [bold white on magenta]     Welcome to Your Personalized Playlist Creator!      [/bold white on magenta]
        """)
        
    print("""
            [cyan]Are you feeling happy or sad? (h/s): [/cyan]
        """)
    mood = input("Your Choice: ").strip().lower()
    while mood not in ["h", "s", "happy", "sad"]:
        print("[red]Invalid input. Please enter 'h' for happy or 's' for sad. [/red]")
        print("""
            [cyan]Are you feeling happy or sad? (h/s): [/cyan]
        """)
        mood = input("Your Choice: ").strip().lower()

    mood = 1 if mood in ["h", "happy"] else 0
    if mood ==1:
        print("""
                [cyan]Do you feel like dancing? (y/n): [/cyan]
            """)
    else:
        print("""
                [cyan]Do you want to dance to feel better? (y/n): [/cyan]
            """)
    dance = input("Your Choice: ").strip().lower()
    while dance not in ["yes", "y", "no", "n"]:
        print("[red]Invalid input. Please enter 'y' or 'n'. [/red]")
        
        if mood ==1:
            print("""
                    [cyan]Do you feel like dancing? (y/n): [/cyan]
                """)
        else:
            print("""
                    [cyan]Do you want to dance to feel better? (y/n): [/cyan]
                """)
                
        dance = input("Your Choice: ").strip().lower()

    print("""
            [cyan]Do you prefer Lyrics, instrumentals or both? (l/i/b): [/cyan]
        """)
    lyrics = input("Your Choice: ").strip().lower()
    while lyrics not in ["lyrics", "l", "instrumentals", "i", "both", "b"]:
        print("[red]Invalid input. Please enter 'l', 'i', or 'b'. [red]")
        print("""
            [cyan]Do you prefer Lyrics, instrumentals or both? (l/i/b): [/cyan]
        """)
        lyrics = input("Your Choice: ").strip().lower()

    print("""
            [cyan]Do you prefer electronic or acoustic music? (e/a): [/cyan]
        """)
    acoustic = input("Your Choice: ").strip().lower()
    while acoustic not in ["electronic", "e", "acoustic", "a"]:
        print("[red]Invalid input. Please enter 'e' or 'a'. [/red]")
        print("""
            [cyan]Do you prefer electronic or acoustic music? (e/a): [/cyan]
        """)
        acoustic = input("Your Choice: ").strip().lower()

    print("""
            [cyan]Do you like rap music? (y/n): [/cyan]
        """)
    rap = input("Your Choice: ").strip().lower()
    while rap not in ["yes", "y", "no", "n"]:
        print("[red]Invalid input. Please enter 'y' or 'n'. [/red]")
        print("""
            [cyan]Do you like rap music? (y/n): [/cyan]
        """)
        rap = input("Your Choice: ").strip().lower()
    return {"mood": mood, "dance": dance, "lyrics": lyrics, "acoustic": acoustic, "rap": rap}

def generate_playlist(preferences):
        
    valence, bpm, mode, dance, energy = "=", "=", "Major", "=", "="
    if preferences["dance"] in ["yes", "y"]:
        valence, bpm, dance, energy = ">=", ">=", ">=", ">="
    elif preferences["mood"] == 0 and preferences["dance"] in ["no", "n"]:
        valence, bpm, mode, dance, energy = "<=", "<=", "Minor", "<=", "<="
    
    elif preferences["mood"] == 1 and preferences["dance"] in ["no", "n"]:
        valence, bpm, mode, dance, energy = ">=", "<=", "Major", "<=", "<="

    inst_range = [0, 30] if preferences["lyrics"] in ["lyrics", "l"] else [70, 100] if preferences["lyrics"] in ["instrumentals", "i"] else [30, 70]
    rap = "DESC" if preferences["rap"] in ["yes", "y"] else "ASC"
    acoustic = ">=" if preferences["acoustic"] in ["acoustic", "a"] else "<="

    query8 = f"""
            SELECT 
                t.track_name,
                GROUP_CONCAT(a.artist_name SEPARATOR ', ') AS artists,
                ma.speechiness AS speechiness
            FROM 
                Track t
            JOIN 
                TrackArtist ta ON t.track_id = ta.track_id
            JOIN
                Artist a ON ta.artist_id = a.artist_id
            JOIN 
                TrackMusicalAttributes tma ON t.track_id = tma.track_id
            JOIN 
                MusicalAttributes ma ON tma.music_id = ma.music_id
            WHERE 
                ma.valence {valence} 50 
                AND ma.bpm {bpm} 120
                AND ma.energy {energy} 70 
                AND ma.danceability {dance} 60 
                AND ma.instrumentalness BETWEEN {inst_range[0]} AND {inst_range[1]}
                AND ma.acousticness {acoustic} 50 
                AND ma.mode = '{mode}'
            GROUP BY
                t.track_name, speechiness
            ORDER BY 
                speechiness {rap}   
            LIMIT 5;
    """

    alt_query = """
        SELECT
            T.track_name,
            a.artist_name
        FROM
            Track T
        JOIN TrackArtist ta ON T.track_id = ta.track_id
        JOIN Artist a ON ta.artist_id = a.artist_id
        JOIN StreamingMetric sm ON t.track_id = sm.track_id
        WHERE sm.platform_id = 1 AND sm.metric_type = 'streams'
        ORDER BY sm.metric_value DESC
        LIMIT 5;
    """
    cursor.execute(query8)
    songs = cursor.fetchall()

    if not songs or len(songs) < 3:
        print("""
            [green]
            Your tastes must be very unique!
            No songs matching your criteria could be found.
            Here's a playlist that includes songs enjoyed by most users: 
            [/green]
        """)
        cursor.execute(alt_query)
        songs = cursor.fetchall()
        return songs

    else:
        print("""
            [green]
            Here is your personalized Playlist!
            [/green]
        """)
        
    return songs


# --- --- --- ALL QUERY INFORMATION --- --- ---


queries = {
    "1": {
        "description": "[blue]Query 1: [/blue]Comparison of Track Analytics by Season of Release.",
        "query": query1,
        "explanation": """
            This SQL query looks at how musical attributes vary across seasons, based on the month
            songs were released. It groups the results into Winter, Spring, Summer, and Fall, providing
            details like the average beats per minute (BPM), the percentage of songs in major and minor
            keys, and averages for characteristics like valence, energy, danceability, acousticness,
            liveness, and speechiness. The data comes from a database that links tracks with their
            musical attributes, offering valuable insights into seasonal trends for music analysis
            or industry decision-making.
        """,
        "dataframe": ["Season", "Avg BPM", "Major Key %", "Minor Key %", 
                     "Avg Valence", "Avg Energy", "Avg Danceability", 
                    "Avg Acousticness", "Avg Liveness", "Avg Speechiness"
                     ]
    },
    "2": {
        "description": "[blue]Query 2: [/blue]Top Artists Based on Weighted Streaming Metrics Across Platforms",
        "query": query2,
        "explanation":  """
            This query looks at how a track's danceability affects its popularity on playlists for a
            specific platform. It sorts tracks into danceability ranges, calculates the average playlist
            count for each range, and flags tracks that perform way above or below the average.
            The results highlight the tracks that stand out the most based on their danceability.
        """,
        "dataframe": ["Artist", "Weighted Score"]
    },
    "3": {
        "description": "[blue]Query 3: [/blue]Analyzing Playlist Popularity by Danceability with Significant Deviations",
        "query": query3,
        "explanation":  """
            This query ranks the top 10 artists across platforms like Spotify, Apple, Deezer, and Shazam by
            calculating a weighted score. It adjusts metrics like playlist appearances, chart rankings,
            and Spotify streams based on each platform's averages and variations, creating a fair and
            comprehensive ranking of artist performance.
        """,
        "dataframe": ['Track', 'Danceability %', 'Danceability Range', 'Playlists',
                      'Avg Playlists for Dancebility', 'Playlists w.r.t. Standard Deviation',
                      'Z-Score Deviation'
                    ]
    },
    "4": {
        "description": "[blue]Query 4: [/blue]High-Intensity Workout Playlist With Increasing BPM",
        "query": query4,
        "explanation":  """
            This query generates a workout playlist featuring tracks with increasing BPM.
            The tracks are selected based on high valence, energy, and danceability, ensuring
            they are upbeat and rhythmic. The playlist also filters out tracks with low
            acousticness, speechiness, and liveness, favoring synthetic and studio-recorded music.
            
            The results are ordered by BPM, from the lowest to the highest, for progressively intense workouts.

            [cyan]Type "Spoti" on MAIN MENU for a surprise.[/cyan]
        """,
        "dataframe": ['Track Name', 'Artist(s)', 'BPM']
    },
    "5": {
        "description": "[blue]Query 5: [/blue]Top Charting Tracks Across Platforms",
        "query": query5,
        "explanation":  """
            This query finds tracks that made it to the top 10 charts on Spotify, Apple Music, and Deezer.
            For each track, it collects details like the track's name, a combined list of its artists,
            its key signature, and its musical mode. It also shows the best chart position for the track on each
            platform. The results are grouped by track and sorted by their rankings, offering a clear picture of 
            the musical traits of hits that succeeded across multiple platforms.
        """,
        "dataframe": ['Track Name', 'Artist(s)', 'Key', 'Mode', 'Spotify Rank', 'Apple Music Rank', 'Deezer Rank']
    },
    "6": {
        "description": "[blue]Query 6: [/blue]High-Energy, Low-Speechiness Tracks on Spotify’s Top 20",
        "query": query6,
       "explanation":  """
            This query focuses on high-energy tracks with low speechiness that are ranked in Spotify's top 20 charts.
            For each track, it pulls the name, a combined list of contributing artists, its energy and speechiness
            percentages, and its Spotify chart position. Only tracks with energy above 70'%' and speechiness below 10'%'
            are included. The results are grouped by track and sorted to show the most energetic songs first, followed
            by the best chart rankings, offering a glimpse at some of Spotify’s most vibrant and engaging hits.
        """,
        "dataframe": ['Track Name', 'Artists', 'Energy', 'Speechiness', 'Spotify Chart Rank']
    },
    "7": {
        "description": "[blue]Query 7:[/blue] Uplifting and Danceable Tracks in Spotify’s Top 25",
        "query": query7,
        "explanation":  """
            This query highlights tracks in Spotify’s top 25 charts that are exceptionally danceable and uplifting.
            It pulls the track’s name, a sorted list of its artists, danceability and valence scores (which reflect
            how energetic and happy the song feels), and its Spotify ranking. Only tracks with danceability and valence
            scores above 80 are included. The results are organized by track and sorted to prioritize the most danceable
            and cheerful songs, offering a look at some of the most feel-good hits on Spotify right now.


        """,
        "dataframe": ['Track', 'Artist(s)', 'Danceability %', 'Valence &', 'Spotify Rank']
    },
    "8": {
        "description": "[blue]Query 8: [/blue]Dynamic Music Playlist Generator",
        "query": """
        SELECT
            T.track_name,
            a.artist_name
        FROM
            Track T
        JOIN TrackArtist ta ON T.track_id = ta.track_id
        JOIN Artist a ON ta.artist_id = a.artist_id
        JOIN StreamingMetric sm ON t.track_id = sm.track_id
        WHERE sm.platform_id = 1 AND sm.metric_type = 'streams'
        ORDER BY sm.metric_value DESC
        LIMIT 5;
        """,
        "explanation":  """
            This music recommendation system gathers user preferences—such as mood, danceability,
            lyric preference, and acoustic style—to create personalized playlists. This query
            filters tracks based on musical attributes like valence, BPM, energy, and speechiness,
            ensuring tailored recommendations. 
            
            If no matches are found, the system defaults to popular chart-toppers.
        """,
        "dataframe": ["Track Name", "Artist(s) Name"]
    }
}


# --- --- --- PREPARE DATA REPRESENTATION AND PRESET VARIABLES --- --- ---


console = Console()

# Function to display DataFrame with Rich
def display_dataframe(df, title="DataFrame Output"):
    """
    Display a Pandas DataFrame in the terminal using Rich with alternating row colors.
    """
    table = Table(title=title, show_lines=True, title_style="bold magenta")

    # Add columns
    for column in df.columns:
        table.add_column(column, style="cyan", justify="center", overflow="fold")

    # Add rows with alternating colors
    for i, (_, row) in enumerate(df.iterrows()):
        row_style = "blue" if i % 2 == 0 else "green"
        table.add_row(*[str(item) for item in row], style=row_style)

        # one blue, one green row for better legibility

    # Print the table
    console.print(table)

ProgramRunning = True # to exit program when needed... or bored
QueriesRunning = False # to easily switch between menus
menuSelector = "main"
Connected = False
FileCorrect = False
Creds = False
File = False


# --- --- --- MAIN PROGRAM SCRIPT --- --- ---
                

if __name__ == "__main__":
# start of program
    
    while ProgramRunning:

        # MAIN MENU
        if menuSelector == "main":

            print("""
                  

[bold white on magenta]                                     MAIN MENU                                     [/bold white on magenta]
                  
            [white]Welcome! Initiate the Program, or Exit.[/white]
            [italic]Best viewed with an extended Terminal.[/italic]
                  
            [bold blue](i)[/bold blue] [bold white]Initialize[/bold white]
            [bold magenta](m)[/bold magenta] [bold white]Miscellaneous[/bold white]
            [bold red](s)[/bold red] [bold white]Stop[/bold white]
                  
            """)
            menuSelector = input("Your Choice: ").strip().lower()
            # ask user to execute or stop the program

        # stop running the program
        elif menuSelector in ["s", "stop"]:

            while True:

                print("""
            [bold red]Are you sure you want to EXIT the program? (y/n)[/bold red]
            """)
                ans = input("Your Choice: ").strip().lower()

                if ans in ["y", "yes"]:
                    loading()
                    ProgramRunning = False # stops
                    break

                elif ans in ["n", "no"]: #otherwwise returns to MAIN MENU
                    print("""
            [blue]Operation cancelled.[/blue]
            """)
                    break
                
                else:
                    print("""
            [red]Invalid Choice.[/red]
            """)
            
            if ans in ["n", "no"]:
                menuSelector = "main"
                

        elif menuSelector in ["i", "init", "initialize", "initiate"]:
        # if user prompts to run the program
            
            try:
                conn = connect_db()
                cursor = conn.cursor()
                Connected = True

                try:
                    drop_database(cursor, "spotify_db")
                    runProgram()
                    FileCorrect = True

                except:
                    FileCorrect = False

            except:
                Connected = False
        
            # if the SQL connection IS established
            if Connected:

                # AND the Filepath IS correct
                if FileCorrect:
                    print("""              
            [blue]SQL and Filepath connection already established. 
            Now showing the QUERIES.[/blue]
            """)  
                    menuSelector = "superSecureRedirectionQue"
                    # redirect to queries

                # BUT the Filepath IS NOT correct
                else:
                    print("""            
            [blue]SQL Connection already established.
            File not found. Please enter filepath below:[/blue]
            """)
                    File = True
                    menuSelector = "superSecureRedirectionFil"
                    # redirect to the filepath corrector

            else:
                print("""
            [blue]SQL connection unsuccessful. Please enter credentials below:[/blue]
            """)
                Creds = True
                menuSelector = "superSecureRedirectionCon"
                # redirect to connection corrector

        elif menuSelector in ["superSecureRedirectionCon"]:

            # only if connection previously established:
            if Connected:
                while True:

                    # ask user to change credentials, it is permanent
                    print("""
            [bold red]All progress will be lost. Proceed? (y/n):[/bold red]
            """)
                    ans = input("Your choice: ").strip().lower()

                    # continue
                    if ans in ["y", "yes"]:
                        drop_database(cursor, "spotify_db")
                        print("""
            [blue]Reset confirmed.[/blue]
            """)
                        # reset Connected value to False
                        Connected = False
                        # run CREDENTIALS 
                        break

                    # cancel
                    elif ans in ["n", "no"]:
                        print("""
            [blue]Reset cancelled.[/blue]
            """)
                        break

                    # ask again
                    else:
                        print("""
            [red]Invalid choice.[/red]
            """)
                        
                if ans in ["n", "no"]:
                    menuSelector = "main"

            # CREDENTIALS
            # if the reset is confirmed, or redirected from a different menu, the code below runs
            Creds = True
            while Creds:

                # prompt user for username, password, and host input
                try:
                    # gets username info
                    username = input("""
            Enter Username, or use default "root" (r): 
            """)
                    # user-friendly input conversion
                    if username.strip().lower() in ["", "r"]:
                        username = "root" 

                    # gets and hides password input
                    password = getpass.getpass("""
            Enter Password (Hidden): 
            """)
                    # confirm to user
                    print("""
            [blue]Password entered...[/blue]
            """)
                    # gets host info
                    host = input("""
            Enter host, or choose default "localhost" (l): 
            """)
                    # user-friendly input conversion
                    if host.strip().lower() in ["", "localhost", "local", "l"]:
                        host = "localhost" 

                    # places new entries in the config dictionary
                    config["user"] = username
                    config["password"] = password
                    config["host"] = host

                    # try establishing the connection
                    conn = connect_db()
                    cursor = conn.cursor()
                    print("""
            [blue]SQL connection established.[/blue]
            """)
                    # update values to exit menu 
                    Creds = False
                    Connected = True
                    if not FileCorrect:
                        File = True
                        menuSelector = "superSecureRedirectionFil"
                    else:
                        menuSelector = "superSecureRedirectionQue"

                # only runs if the sql connection is unsuccessful
                except:
                    while True:

                        print(("""
            [bold red]Access denied. Retry (r) or EXIT program (e):[/bold red]
            """))
                        # prompt for a different answer
                        ans = input("Your Choice: ").strip().lower()

                        if ans in ["r", "retry"]:
                            break

                        elif ans in ["e", "exit"]:
                            Creds = False
                            break

                        else:
                            print(("""
            [red]Invalid choice.[/red]
            """))
                    if ans in ["e", "exit"]:
                        menuSelector = "stop"
        
        elif menuSelector == "superSecureRedirectionFil":

            if Connected:

                if FileCorrect:

                    while True:

                        # ask user to change filepath, it is permanent
                        print("""
            [bold red]All progress will be lost. Proceed? (y/n):[/bold red]
            """)
                        ans = input("Your choice: ").strip().lower()

                        # continue
                        if ans in ["y", "yes"]:
                            print("""
            [blue]Reset confirmed.[/blue]
            """)
                            # reset Connected value to False
                            FileCorrect = False
                            # run FILEPATH 
                            break

                        # cancel
                        elif ans in ["n", "no"]:
                            print("""
            [blue]Reset cancelled.[/blue]
            """)
                            break

                        # ask again
                        else:
                            print("""
            [red]Invalid choice.[/red]
             """)
                            
                    if ans in ["n", "no"]:
                        menuSelector = "main"
                
                File = True
                while File:
                    try:
                        print("""
            Enter Filepath: 
            """)
                        ans = input("Your Choice: ").strip().lower()
                        
                        filepath = ans
                        drop_database(cursor, "spotify_db")
                        runProgram()
                        print("""
            [blue]Filepath correct.
            Now showing the QUERIES.[/blue]
            """)
                        FileCorrect = True
                        choiceSet = None
                        menuSelector = "superSecureRedirectionQue"
                        File = False
                    except:
                        while True:
                            print("""
            [bold red]File not found. Retry (r) or EXIT program (e):[/bold red]
            """)
                            ans = input("Your choice: ").strip().lower()

                            if ans in ["r", "retry"]:
                                break

                            elif ans in ["e", "exit"]:
                                File = False
                                break

                            else:
                                print( "Invalid choice.")
                        
                        if ans in ["e", "exit"]:
                            menuSelector = "stop"
    
            else:
                print("""
            [blue]Establish SQL connection before adding a Filepath.[/blue]
            """)
                menuSelector = "superSafeRedirectionCon"
                    
        elif menuSelector == "superSecureRedirectionQue":

            QueriesRunning = True
            while QueriesRunning:

                print("""
                      

[bold white on magenta]                                  QUERIES MENU                                  [/bold white on magenta]  
                                          
            View All Queries, Explore a Query, or Exit the Program.
                      
                [bold blue](v)[/bold blue] [bold white]View[/bold white]
                [bold blue](1-8)[/bold blue] [bold white]Explore[/bold white]
                [magenta](b)[/magenta] [bold white]Back to[/bold white] [magenta]MAIN MENU[/magenta]
                [bold red](s)[/bold red] [bold white]Stop[/bold white]
                      
            """)
                choiceQuery = input("Your choice: ").strip().lower()

                # EXIT the loop if "stop" is entered
                if choiceQuery in ["stop", "s"]:
                    menuSelector = "stop"
                    QueriesRunning = False

                elif choiceQuery in ["back", "b"]:
                    menuSelector = "main"
                    QueriesRunning = False
                
                # show the list of queries if "view" is entered
                elif choiceQuery in ["view", "v"]:
                    print("""
            [bold blue]Available Queries:[/bold blue]""")
                    
                    for key, value in queries.items():
                        print(f"""
            [green]{value['description']}[/green]""")
                    print()

                # proceed if the choice is a valid query number...
                elif choiceQuery in queries:
                    print(f"""
            [green]{queries[choiceQuery]['description']}[/green]""")
                    print("""
            [white]Would you like to 'Run' the query or 'Explore' it?
                          
                [bold blue](r)[/bold blue] [bold white]Run[/bold white]
                [bold blue](e)[/bold blue] [bold white]Explore[/bold white]
            [/white]
            """)
                    # ask the user if they want to run or explore the query
                    action = input("Your Choice: ").strip().lower()
                    print() # empty line for aesthetics

                    if action in ["run", "r"]:
                        query = queries[choiceQuery]["query"]

                        if choiceQuery == "8":   
                            try:
                                songs = generate_playlist(get_user_preferences())
                                results = [row[:2] for row in songs]
                            except:
                                print("[blue]An exception occurred.[/blue]")
                                menuSelector = "main"
                                QueriesRunning = False
                        else:
                            cursor.execute(query)
                            results = cursor.fetchall()
                        
                        # display results
                        if results:
                            try:
                                df = pd.DataFrame(results, columns=queries[choiceQuery]['dataframe'])

                                display_dataframe(df, title=queries[choiceQuery]['description'])

                                print("[italic]Best viewed with an extended Terminal.[/italic]")

                                # Display the DataFrame in the terminal 
                            except:
                                print("[blue]No data found for this query.[/blue]")
                        else:
                            print("/blue]No data found for this query.[/blue]")

                    elif action in ["explore", "e"]:
                        exp = queries[choiceQuery]['explanation']
                        print(f"[green italic]{exp}[/green italic]")
                            
                    elif action in ["stop", "s"]:
                        menuSelector = "stop"
                        QueriesRunning = False

                    else:
                        print("[red]Invalid choice.[/red]")
                
                else:
                    print("[red]Invalid choice.[/red]")
        
        elif menuSelector in ["supersecureredirectioncon", "supersecureredirectionfil", "supersecureredirectionque"]:
            print("[bold white on red]  Redirection request was denied.  [/bold white on red]")
            menuSelector = "main"

        elif menuSelector in ["m", "misc", "miscellaneous"]:
            print("""
        Menus are [magenta]Magenta[/magenta],
        Feedback is given in [blue]Blue[/blue],
        Outputs are [green]Green[/green],
        Invalidity errors are [red]Red[/red],
        Hacking requests are denied with [bold white on red] Red [/bold white on red].
        
        Some outputs are replaced with "?". THis is due to the wncoding of the file.
        We applied different readings for different encodings. Since the csv file
        itself is encoded with "utf-8"-read errors, we replaced them with a common
        character.
                  
        [green]Check the code for an Easter Egg HERE.
        Or find the hidden password to print it.[/green]
        """)
            menuSelector = "main"
        
        elif menuSelector == "spoti":
            print("""[bold green]                                                           
                                        ------------------                                        
                                 --------------------------------                                 
                            ------------------------------------------                            
                         ------------------------------------------------                         
                      ------------------------------------------------------                      
                    ----------------------------------------------------------                    
                  --------------------------------------------------------------                  
                ------------------------------------------------------------------                
               --------------------------------------------------------------------               
             ------------------------------------------------------------------------             
            ----------------                               ---------------------------            
           -----------                                             --------------------           
          -----------                                                    ---------------          
          -----------             -------------------                        -----------          
         -------------------------------------------------------               ----------         
         -------------------------------------------------------------         ----------         
        -------------------------                  -----------------------   -------------        
        -----------------                                    -----------------------------        
        ----------------                                           -----------------------        
        ----------------       ----------------------                  -------------------        
        -----------------------------------------------------            -----------------        
         ---------------------------------------------------------       ----------------         
         -------------------------                 --------------------------------------         
          ----------------                                 -----------------------------          
          ---------------               ------                  ------------------------          
           ----------------------------------------------           -------------------           
            --------------------------------------------------      ------------------            
             ------------------------------------------------------------------------             
               --------------------------------------------------------------------               
                ------------------------------------------------------------------                
                  --------------------------------------------------------------                  
                    ----------------------------------------------------------                    
                      ------------------------------------------------------                      
                         ------------------------------------------------                         
                            ------------------------------------------                            
                                 --------------------------------                                 
                                        ------------------                                        
            [/bold green]""")
            menuSelector = "main"

        else:
            print("""
            [bold red]Invalid Choice.[/bold red]
            """)
            menuSelector = "main"
        
            




