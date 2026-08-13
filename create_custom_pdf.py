import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

MOVIES_DATA = [
    {
        "title": "Inception",
        "year": 2010,
        "director": "Christopher Nolan",
        "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page", "Tom Hardy", "Ken Watanabe"],
        "genres": ["Sci-Fi", "Action", "Psychological Thriller"],
        "themes": ["Dreams and Reality", "Subconscious Mind", "Memory and Loss", "Time Manipulation"],
        "awards": ["Oscar (Best Cinematography)", "Oscar (Best Visual Effects)", "Oscar (Best Sound Editing)", "Oscar (Best Sound Mixing)"]
    },
    {
        "title": "The Dark Knight",
        "year": 2008,
        "director": "Christopher Nolan",
        "actors": ["Christian Bale", "Heath Ledger", "Aaron Eckhart", "Michael Caine", "Gary Oldman", "Morgan Freeman"],
        "genres": ["Action", "Crime", "Drama"],
        "themes": ["Heroism and Chaos", "Justice and Morality", "Duality and Corruption"],
        "awards": ["Oscar (Best Supporting Actor)", "Oscar (Best Sound Editing)"]
    },
    {
        "title": "Interstellar",
        "year": 2014,
        "director": "Christopher Nolan",
        "actors": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain", "Michael Caine", "Matt Damon"],
        "genres": ["Sci-Fi", "Drama", "Adventure"],
        "themes": ["Space Exploration", "Love Across Dimensions", "Time Dilation", "Human Survival"],
        "awards": ["Oscar (Best Visual Effects)"]
    },
    {
        "title": "Oppenheimer",
        "year": 2023,
        "director": "Christopher Nolan",
        "actors": ["Cillian Murphy", "Emily Blunt", "Matt Damon", "Robert Downey Jr.", "Florence Pugh"],
        "genres": ["Biography", "Drama", "History"],
        "themes": ["Atomic Age", "Scientific Ethics", "Political Betrayal", "Guilt and Consequences"],
        "awards": ["Oscar (Best Picture)", "Oscar (Best Director)", "Oscar (Best Actor)", "Oscar (Best Supporting Actor)"]
    },
    {
        "title": "Avatar",
        "year": 2009,
        "director": "James Cameron",
        "actors": ["Sam Worthington", "Zoe Saldana", "Sigourney Weaver", "Stephen Lang"],
        "genres": ["Sci-Fi", "Action", "Adventure"],
        "themes": ["Environmentalism", "Alien Colonization", "Connection with Nature", "Imperialism"],
        "awards": ["Oscar (Best Art Direction)", "Oscar (Best Cinematography)", "Oscar (Best Visual Effects)"]
    },
    {
        "title": "Titanic",
        "year": 1997,
        "director": "James Cameron",
        "actors": ["Leonardo DiCaprio", "Kate Winslet", "Billy Zane", "Kathy Bates"],
        "genres": ["Romance", "Drama"],
        "themes": ["Class Struggle", "Forbidden Love", "Tragic Disaster", "Sacrifice"],
        "awards": ["Oscar (Best Picture)", "Oscar (Best Director)", "Oscar (Best Original Score)", "Oscar (Best Visual Effects)"]
    },
    {
        "title": "The Matrix",
        "year": 1999,
        "director": "Lana Wachowski",
        "actors": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss", "Hugo Weaving"],
        "genres": ["Sci-Fi", "Action"],
        "themes": ["Simulated Reality", "Free Will vs Determinism", "Artificial Intelligence", "Chosen One"],
        "awards": ["Oscar (Best Film Editing)", "Oscar (Best Visual Effects)", "Oscar (Best Sound)"]
    },
    {
        "title": "Pulp Fiction",
        "year": 1994,
        "director": "Quentin Tarantino",
        "actors": ["John Travolta", "Samuel L. Jackson", "Uma Thurman", "Bruce Willis"],
        "genres": ["Crime", "Drama"],
        "themes": ["Non-linear Narrative", "Redemption", "Pop Culture", "Underworld Crime"],
        "awards": ["Oscar (Best Original Screenplay)"]
    },
    {
        "title": "Django Unchained",
        "year": 2012,
        "director": "Quentin Tarantino",
        "actors": ["Jamie Foxx", "Christoph Waltz", "Leonardo DiCaprio", "Kerry Washington", "Samuel L. Jackson"],
        "genres": ["Western", "Drama", "Action"],
        "themes": ["Slavery and Freedom", "Revenge", "Bounty Hunting", "Justice"],
        "awards": ["Oscar (Best Supporting Actor)", "Oscar (Best Original Screenplay)"]
    },
    {
        "title": "The Godfather",
        "year": 1972,
        "director": "Francis Ford Coppola",
        "actors": ["Marlon Brando", "Al Pacino", "James Caan", "Robert Duvall"],
        "genres": ["Crime", "Drama"],
        "themes": ["Family Loyalty", "Mafia Power", "Corruption of Innocence", "American Dream"],
        "awards": ["Oscar (Best Picture)", "Oscar (Best Actor)", "Oscar (Best Adapted Screenplay)"]
    },
    {
        "title": "Fight Club",
        "year": 1999,
        "director": "David Fincher",
        "actors": ["Brad Pitt", "Edward Norton", "Helena Bonham Carter"],
        "genres": ["Drama", "Psychological Thriller"],
        "themes": ["Consumerism", "Identity Crisis", "Masculinity", "Rebellion"],
        "awards": ["None"]
    },
    {
        "title": "The Shawshank Redemption",
        "year": 1994,
        "director": "Frank Darabont",
        "actors": ["Tim Robbins", "Morgan Freeman", "Bob Gunton"],
        "genres": ["Drama"],
        "themes": ["Hope and Endurance", "Friendship in Captivity", "Institutionalization", "Justice"],
        "awards": ["None"]
    },
    {
        "title": "Forrest Gump",
        "year": 1994,
        "director": "Robert Zemeckis",
        "actors": ["Tom Hanks", "Robin Wright", "Gary Sinise", "Sally Field"],
        "genres": ["Drama", "Romance"],
        "themes": ["Destiny vs Chance", "Innocence and History", "Unconditional Love"],
        "awards": ["Oscar (Best Picture)", "Oscar (Best Director)", "Oscar (Best Actor)", "Oscar (Best Adapted Screenplay)"]
    },
    {
        "title": "Avengers: Endgame",
        "year": 2019,
        "director": "Anthony Russo",
        "actors": ["Robert Downey Jr.", "Chris Evans", "Mark Ruffalo", "Chris Hemsworth", "Scarlett Johansson", "Tom Holland"],
        "genres": ["Action", "Sci-Fi", "Adventure"],
        "themes": ["Ultimate Sacrifice", "Time Travel", "Heroic Legacy", "Uniting Against Evil"],
        "awards": ["None"]
    },
    {
        "title": "Spider-Man: Into the Spider-Verse",
        "year": 2018,
        "director": "Bob Persichetti",
        "actors": ["Shameik Moore", "Jake Johnson", "Hailee Steinfeld", "Mahershala Ali"],
        "genres": ["Animation", "Action", "Sci-Fi"],
        "themes": ["Multiverse", "Anyone Can Be a Hero", "Mentorship and Loss"],
        "awards": ["Oscar (Best Animated Feature)"]
    },
    {
        "title": "Gladiator",
        "year": 2000,
        "director": "Ridley Scott",
        "actors": ["Russell Crowe", "Joaquin Phoenix", "Connie Nielsen", "Oliver Reed"],
        "genres": ["Action", "Adventure", "Drama"],
        "themes": ["Honor and Vengeance", "Roman Empire", "Gladiator Combat", "Tyranny vs Freedom"],
        "awards": ["Oscar (Best Picture)", "Oscar (Best Actor)", "Oscar (Best Costume Design)"]
    },
    {
        "title": "3 Idiots",
        "year": 2009,
        "director": "Rajkumar Hirani",
        "actors": ["Aamir Khan", "R. Madhavan", "Sharman Joshi", "Kareena Kapoor", "Boman Irani"],
        "genres": ["Comedy", "Drama"],
        "themes": ["Education System Reform", "Pursuing Passion", "Friendship", "Pressure and Expectations"],
        "awards": ["Filmfare (Best Film)", "Filmfare (Best Director)"]
    },
    {
        "title": "RRR",
        "year": 2022,
        "director": "S.S. Rajamouli",
        "actors": ["N.T. Rama Rao Jr.", "Ram Charan", "Ajay Devgn", "Alia Bhatt"],
        "genres": ["Action", "Drama"],
        "themes": ["Anti-Colonial Resistance", "Brotherhood", "Revolution", "Mythological Symbolism"],
        "awards": ["Oscar (Best Original Song)"]
    },
    {
        "title": "Dangal",
        "year": 2016,
        "director": "Nitesh Tiwari",
        "actors": ["Aamir Khan", "Fatima Sana Shaikh", "Sanya Malhotra", "Zaira Wasim"],
        "genres": ["Biography", "Drama", "Sport"],
        "themes": ["Women Empowerment", "Father Daughter Relationship", "Wrestling Discipline", "Patriotism"],
        "awards": ["Filmfare (Best Film)", "Filmfare (Best Director)", "Filmfare (Best Actor)"]
    },
    {
        "title": "KGF: Chapter 1",
        "year": 2018,
        "director": "Prashanth Neel",
        "actors": ["Yash", "Srinidhi Shetty", "Ramachandra Raju"],
        "genres": ["Action", "Crime"],
        "themes": ["Gold Mine Exploitation", "Rise to Power", "Promise to Mother", "Rebellion"],
        "awards": ["National Film Award (Best Action Direction)", "National Film Award (Best Special Effects)"]
    },
    {
        "title": "Sholay",
        "year": 1975,
        "director": "Ramesh Sippy",
        "actors": ["Dharmendra", "Amitabh Bachchan", "Sanjeev Kumar", "Hema Malini", "Jaya Bhaduri", "Amjad Khan"],
        "genres": ["Action", "Adventure", "Drama"],
        "themes": ["Friendship", "Revenge", "Banditry", "Sacrifice"],
        "awards": ["Filmfare (Best Editing)"]
    },
    {
        "title": "Lagaan",
        "year": 2001,
        "director": "Ashutosh Gowariker",
        "actors": ["Aamir Khan", "Gracy Singh", "Rachel Shelley", "Paul Blackthorne"],
        "genres": ["Drama", "Sport"],
        "themes": ["Cricket Match Against British Rule", "Unity in Diversity", "Overcoming Oppression"],
        "awards": ["Filmfare (Best Film)", "Filmfare (Best Director)", "Filmfare (Best Actor)"]
    },
    {
        "title": "Pathaan",
        "year": 2023,
        "director": "Siddharth Anand",
        "actors": ["Shah Rukh Khan", "Deepika Padukone", "John Abraham", "Dimple Kapadia", "Salman Khan"],
        "genres": ["Action", "Thriller"],
        "themes": ["Espionage", "Patriotism", "Rogue Agent", "Global Threat"],
        "awards": ["Filmfare (Best Action)", "Filmfare (Best VFX)"]
    },
    {
        "title": "Jawan",
        "year": 2023,
        "director": "Atlee",
        "actors": ["Shah Rukh Khan", "Nayanthara", "Vijay Sethupathi", "Deepika Padukone", "Sanya Malhotra"],
        "genres": ["Action", "Thriller"],
        "themes": ["Social Justice", "Corrupt Systems", "Vigilante Hero", "Father Son Dual Role"],
        "awards": ["Filmfare (Best Action)"]
    },
    {
        "title": "Brahmastra",
        "year": 2022,
        "director": "Ayan Mukerji",
        "actors": ["Ranbir Kapoor", "Alia Bhatt", "Amitabh Bachchan", "Nagarjuna Akkineni", "Shah Rukh Khan"],
        "genres": ["Action", "Adventure", "Fantasy"],
        "themes": ["Indian Mythology", "Astraverse Powers", "Love as Ultimate Power"],
        "awards": ["National Film Award (Best VFX)", "National Film Award (Best Music Direction)"]
    }
]

def generate_pdf(output_path: str = "./data/custom_movies.pdf"):
    """Generate custom PDF containing iconic movies."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    normal_style = styles["Normal"]
    normal_style.fontSize = 11
    normal_style.leading = 14

    story = []

    for movie in MOVIES_DATA:
        text_lines = [
            f"Movie Title: {movie['title']}",
            f"Release Year: {movie['year']}",
            f"Director: {movie['director']}",
            "Actors:"
        ]
        for actor in movie["actors"]:
            text_lines.append(f"- {actor}")
        
        text_lines.append("Genre:")
        for genre in movie["genres"]:
            text_lines.append(f"- {genre}")
            
        text_lines.append("Themes:")
        for theme in movie["themes"]:
            text_lines.append(f"- {theme}")

        text_lines.append("Awards:")
        for award in movie["awards"]:
            text_lines.append(f"- {award}")

        text_lines.append("-" * 40)
        
        content = "<br/>".join(text_lines)
        story.append(Paragraph(content, normal_style))
        story.append(Spacer(1, 15))

    doc.build(story)
    print(f"✅ Generated custom movies PDF with {len(MOVIES_DATA)} iconic movies at: {output_path}")

if __name__ == "__main__":
    generate_pdf()
