from flask import Flask, render_template, request, url_for
from rdflib import Graph, Namespace, RDF, XSD

app = Flask(__name__)

# Load RDF Data
g = Graph()
g.parse("data\\tourism.ttl", format="turtle")

EX = Namespace("http://example.org/tourism#")


def build_filters(form):
    filters = []

    category = form.get("category")
    budget = form.get("budget")
    season = form.get("season")
    state = form.get("state")
    duration = form.get("duration")
    min_rating = form.get("rating")

    if category and category != "Any":
        filters.append(f'?city rdf:type ex:{category}City .')

    if budget and budget != "Any":
        filters.append(f'FILTER(LCASE(?budget) = "{budget.lower()}")')

    if season and season != "Any":
        filters.append(f'FILTER(LCASE(?season) = "{season.lower()}")')

    if state and state != "":
        filters.append(f'FILTER(?state = "{state}")')

    if duration and duration != "Any":
        filters.append(f'FILTER(LCASE(?duration) = "{duration.lower()}")')

    if min_rating:
        try:
            r = float(min_rating)
            filters.append(f'FILTER(xsd:decimal(?rating) >= {r})')
        except ValueError:
            pass

    return filters
@app.route("/")
def index():
    return render_template("index.html")
@app.route("/login")
def login():
    return render_template("login.html")



@app.route('/home')
def home():
    # Extract categories dynamically from RDF types
    categories = ['Any']
    for t in g.subjects(RDF.type, None):
        if "City" in str(t):
            c = str(t).split('#')[-1].replace("City", "")
            if c and c not in categories:
                categories.append(c)

    # Budget options
    budgets = sorted(set([str(o).lower() for o in g.objects(None, EX.budget)]))
    budgets = ["Any"] + [b.capitalize() for b in budgets if b]

    # States
    states = sorted(set([str(s) for s in g.objects(None, EX.state)]))
    states = [""] + states

    # Durations
    durations = sorted(set([str(d) for d in g.objects(None, EX.duration)]))
    durations = ["Any"] + durations

    return render_template('home.html', categories=categories,
                           budgets=budgets, states=states, durations=durations)


@app.route('/recommend', methods=['POST'])
def recommend():
    form = request.form
    filters = build_filters(form)

    query = '''
    PREFIX ex: <http://example.org/tourism#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?city ?label ?attraction ?image ?budget ?season ?duration ?rating ?state WHERE {
        ?city ex:label ?label .
        OPTIONAL { ?city ex:hasAttraction ?attraction }
        OPTIONAL { ?city ex:image ?image }
        OPTIONAL { ?city ex:budget ?budget }
        OPTIONAL { ?city ex:bestSeason ?season }
        OPTIONAL { ?city ex:duration ?duration }
        OPTIONAL { ?city ex:rating ?rating }
        OPTIONAL { ?city ex:state ?state }

        %s
    }
    ORDER BY DESC(xsd:decimal(?rating))
    LIMIT 50
    ''' % ('\n'.join(filters) if filters else '')

    results = g.query(query)

    # Group results: each city -> details + list of attractions
    cities = {}
    for row in results:
        city_uri = str(row.city)
        label = str(row.label)
        if city_uri not in cities:
            cities[city_uri] = {
                'label': label,
                'image': str(row.image) if row.image else None,
                'budget': str(row.budget) if row.budget else None,
                'season': str(row.season) if row.season else None,
                'duration': str(row.duration) if row.duration else None,
                'rating': float(row.rating) if row.rating else None,
                'state': str(row.state) if row.state else None,
                'attractions': []
            }
        if row.attraction:
            cities[city_uri]['attractions'].append(str(row.attraction))

    return render_template('results.html', cities=cities.values(), criteria=form)


if __name__ == '__main__':
    app.run(debug=True)
