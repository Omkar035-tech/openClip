import os
import sys
import json
import urllib.request
import urllib.parse
import soundfile as sf
import numpy as np
import librosa

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(BASE_DIR, "music_library")
TRACKS_DIR = os.path.join(MUSIC_DIR, "tracks")
SFX_DIR = os.path.join(BASE_DIR, "music_library", "sfx")
os.makedirs(TRACKS_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)

TRACKS_METADATA = [
    {
        "id": "sneaky_snitch",
        "title": "Sneaky Snitch",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sneaky%20Snitch.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Sneaky Snitch" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["playful", "comedy", "banter", "funny", "light"],
        "energy": 6.5,
        "valence": 0.8
    },
    {
        "id": "monkeys_spinning",
        "title": "Monkeys Spinning Monkeys",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Monkeys%20Spinning%20Monkeys.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Monkeys Spinning Monkeys" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["playful", "chaotic", "humor", "comedy", "upbeat"],
        "energy": 7.5,
        "valence": 0.9
    },
    {
        "id": "the_complex",
        "title": "The Complex",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/The%20Complex.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"The Complex" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["tense", "dark", "debate", "driving", "suspense"],
        "energy": 7.0,
        "valence": -0.3
    },
    {
        "id": "heartbreaking",
        "title": "Heartbreaking",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Heartbreaking.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Heartbreaking" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["emotional", "reflective", "sad", "calm", "serious", "piano"],
        "energy": 3.0,
        "valence": -0.7
    },
    {
        "id": "cipher",
        "title": "Cipher",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Cipher.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Cipher" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["tech", "modern", "electronic", "explainer", "steady"],
        "energy": 5.5,
        "valence": 0.4
    },
    {
        "id": "carefree",
        "title": "Carefree",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Carefree" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["uplifting", "cheerful", "inspiring", "warm"],
        "energy": 6.0,
        "valence": 0.85
    },
    {
        "id": "airport_lounge",
        "title": "Airport Lounge",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Airport%20Lounge.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Airport Lounge" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["chill", "lo-fi", "ambient", "conversation", "relaxed"],
        "energy": 4.0,
        "valence": 0.5
    },
    {
        "id": "scheming_weasel",
        "title": "Scheming Weasel (Faster Version)",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Scheming%20Weasel%20faster.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Scheming Weasel (faster version)" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["mischievous", "comedy", "banter", "playful", "sneaky"],
        "energy": 6.8,
        "valence": 0.7
    },
    {
        "id": "volatile_reaction",
        "title": "Volatile Reaction",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Volatile%20Reaction.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Volatile Reaction" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["intense", "energetic", "motivational", "gritty", "discipline", "hard", "driving", "inspiring", "rock"],
        "energy": 9.0,
        "valence": 0.5
    },
    {
        "id": "future_gladiator",
        "title": "Future Gladiator",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Future%20Gladiator.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Future Gladiator" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["epic", "motivational", "intense", "heroic", "strength", "power", "heavy", "inspiring"],
        "energy": 9.2,
        "valence": 0.6
    },
    {
        "id": "hitman",
        "title": "Hitman",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Hitman.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Hitman" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["tense", "dark", "suspense", "focused", "relentless", "gritty", "intense"],
        "energy": 8.0,
        "valence": -0.2
    },
    {
        "id": "hero_down",
        "title": "Hero Down",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Hero%20Down.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Hero Down" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["epic", "intense", "dramatic", "motivational", "heroic", "strength", "powerful"],
        "energy": 8.8,
        "valence": 0.3
    },
    {
        "id": "movement_proposition",
        "title": "Movement Proposition",
        "artist": "Kevin MacLeod",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Movement%20Proposition.mp3",
        "license": "CC-BY 4.0",
        "commercial_ok": True,
        "attribution_required": True,
        "attribution": '"Movement Proposition" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License',
        "moods": ["driving", "intense", "motivational", "relentless", "focus", "discipline", "energetic"],
        "energy": 8.5,
        "valence": 0.4
    }
]

def generate_procedural_sfx():
    # 1. Whoosh SFX (filtered white noise sweep, 0.35s)
    sr = 44100
    dur = 0.35
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    noise = np.random.uniform(-1, 1, len(t))
    # Gaussian amplitude envelope
    env = np.exp(-((t - dur / 2) ** 2) / (2 * (dur / 6) ** 2))
    whoosh = noise * env * 0.4
    sf.write(os.path.join(SFX_DIR, "whoosh.wav"), whoosh, sr)
    
    # 2. Pop SFX (decaying sine chirp, 0.12s)
    dur_pop = 0.12
    t_pop = np.linspace(0, dur_pop, int(sr * dur_pop), endpoint=False)
    freq = np.linspace(600, 200, len(t_pop))
    sine = np.sin(2 * np.pi * freq * t_pop)
    decay = np.exp(-t_pop / 0.03)
    pop = sine * decay * 0.5
    sf.write(os.path.join(SFX_DIR, "pop.wav"), pop, sr)
    print("Generated procedural CC0 SFX: whoosh.wav, pop.wav")

def download_and_index():
    library_index = []
    licenses_index = {}
    
    for t_info in TRACKS_METADATA:
        filename = f"{t_info['id']}.mp3"
        filepath = os.path.join(TRACKS_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"Downloading {t_info['title']}...")
            req = urllib.request.Request(t_info['url'], headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=20) as resp, open(filepath, 'wb') as out_f:
                    out_f.write(resp.read())
                print(f"Downloaded: {filename}")
            except Exception as e:
                print(f"Error downloading {filename}: {e}")
                continue
                
        # Audio feature analysis with librosa
        try:
            y, sr = librosa.load(filepath, sr=22050, duration=60.0)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(np.atleast_1d(tempo)[0])
            beat_times = librosa.frames_to_time(beats, sr=sr).tolist()
            rms = float(np.mean(librosa.feature.rms(y=y)))
            total_duration = float(librosa.get_duration(path=filepath))
        except Exception as e:
            print(f"Warning analyzing {filename}: {e}")
            bpm = 120.0
            beat_times = []
            rms = 0.1
            total_duration = 180.0
            
        entry = {
            "id": t_info['id'],
            "title": t_info['title'],
            "artist": t_info['artist'],
            "file": os.path.relpath(filepath, MUSIC_DIR),
            "bpm": round(bpm, 1),
            "duration": round(total_duration, 2),
            "rms_energy": round(rms, 4),
            "moods": t_info['moods'],
            "energy": t_info['energy'],
            "valence": t_info['valence'],
            "instrumental_only": True,
            "beat_times": beat_times[:40]
        }
        library_index.append(entry)
        
        licenses_index[t_info['id']] = {
            "title": t_info['title'],
            "artist": t_info['artist'],
            "source_url": t_info['url'],
            "license": t_info['license'],
            "commercial_ok": t_info['commercial_ok'],
            "attribution_required": t_info['attribution_required'],
            "attribution": t_info['attribution']
        }
        
    # Write library.json and licenses.json
    with open(os.path.join(MUSIC_DIR, "library.json"), "w") as f:
        json.dump(library_index, f, indent=2)
    with open(os.path.join(MUSIC_DIR, "licenses.json"), "w") as f:
        json.dump(licenses_index, f, indent=2)
        
    print(f"Indexed {len(library_index)} tracks to library.json and licenses.json")

if __name__ == '__main__':
    generate_procedural_sfx()
    download_and_index()
