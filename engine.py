import pandas as pd
import json

def process_stats():
    # Load the CSV you downloaded from Kaggle
    df = pd.read_csv('players_data-2025_2026.csv')
    
    # Select only the columns you actually need for your website
    cols = {
        'Player': 'name',
        'Squad': 'club',
        'Comp': 'league',
        'Pos': 'position',
        'Min': 'minutes',
        'Gls': 'goals',
        'Ast': 'assists',
        'xG': 'xg',
        'xAG': 'xa',
        'PrgP': 'prog_passes',
        'PrgC': 'prog_carries',
        'CrdY': 'yellow_cards'
    }
    
    # Filter and rename
    df_clean = df[list(cols.keys())].rename(columns=cols)
    
    # Save to your structured JSON
    df_clean.to_json("docs/data/players.json", orient="records", indent=2)
    print(f"Processed {len(df_clean)} player records successfully.")

if __name__ == "__main__":
    process_stats()
