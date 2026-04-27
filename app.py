from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from database import session
from models import Recipe
from services.ai_service import generate_text

app = Flask(__name__)
app.secret_key = "dev"

CATEGORIES = ["Breakfast / Доручек", "Lunch / Ручек", "Dinner / Вечера", "Dessert / Десерт"]


def parse_duration(value):
    minutes = int(value)
    if minutes <= 0:
        raise ValueError
    return minutes


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/recipe", methods=["GET", "POST"])
def recipe():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        category = (request.form.get("category") or "").strip()
        things_used = (request.form.get("things_used") or "").strip()
        ingredients = (request.form.get("ingredients") or "").strip()
        steps = (request.form.get("steps") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        time = (request.form.get("time") or "").strip()

        if not name or not category or not things_used or not ingredients or not steps or not time:
            flash("Please fill all required fields. / Ве молиме пополнете ги сите полиња.", "error")
            return render_template("recipe_form.html", recipe=None, categories=CATEGORIES)

        try:
            parsed_time = parse_duration(time)
        except ValueError:
            flash("Cooking time must be a whole number of minutes. / Времето за готбење треба да е цел број.", "error")
            return render_template("recipe_form.html", recipe=None, categories=CATEGORIES)

        recipe = Recipe(
            name=name,
            category=category,
            things_used=things_used,
            ingredients=ingredients,
            steps=steps,
            notes=notes or None,
            time=parsed_time,
        )
        session.add(recipe)
        session.commit()
        return redirect(url_for("recipe_detail", recipe_id=recipe.id))

    return render_template("recipe_form.html", recipe=None, categories=CATEGORIES)


@app.route("/recipes", methods=["GET"])
def recipe_list():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    query = session.query(Recipe)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Recipe.name.ilike(like),
                Recipe.ingredients.ilike(like),
                Recipe.steps.ilike(like),
                Recipe.things_used.ilike(like),
            )
        )

    if category:
        query = query.filter(Recipe.category == category)

    recipes = query.order_by(Recipe.created_at.desc()).all()
    return render_template(
        "recipe_list.html",
        recipes=recipes,
        q=q,
        category=category,
        categories=CATEGORIES,
    )


@app.route("/recipes/<int:recipe_id>", methods=["GET"])
def recipe_detail(recipe_id):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        return "Recipe not found", 404
    return render_template("recipe_detail.html", recipe=recipe)


@app.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
def recipe_edit(recipe_id):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        return "Recipe not found / Рецептата не е пронајдена", 404

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        category = (request.form.get("category") or "").strip()
        things_used = (request.form.get("things_used") or "").strip()
        ingredients = (request.form.get("ingredients") or "").strip()
        steps = (request.form.get("steps") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        time = (request.form.get("time") or "").strip()

        if not name or not category or not things_used or not ingredients or not steps or not time:
            flash("Please fill all required fields.", "error")
            return render_template("recipe_form.html", recipe=recipe, categories=CATEGORIES)

        try:
            parsed_time = parse_duration(time)
        except ValueError:
            flash("Cooking time must be a whole number of minutes. / Времето за готвење треба да биде цел број.", "error")
            return render_template("recipe_form.html", recipe=recipe, categories=CATEGORIES)

        recipe.name = name
        recipe.category = category
        recipe.things_used = things_used
        recipe.ingredients = ingredients
        recipe.steps = steps
        recipe.notes = notes or None
        recipe.time = parsed_time
        session.commit()
        return redirect(url_for("recipe_detail", recipe_id=recipe.id))

    return render_template("recipe_form.html", recipe=recipe, categories=CATEGORIES)


@app.route("/recipes/<int:recipe_id>/delete", methods=["POST"])
def recipe_delete(recipe_id):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        return "Recipe not found", 404
    session.delete(recipe)
    session.commit()
    return redirect(url_for("recipe_list"))

@app.post("/ai/rewrite/<int:recipe_id>")
def ai_rewrite(recipe_id):
    recipe = session.get(Recipe, recipe_id)
    print(recipe)
    if not recipe:
        return "Recipe not found / Рецептата не е пронајдена", 404
    if not recipe.notes or not recipe.ingredients or not recipe.steps or not recipe.things_used:
        return redirect(url_for("recipe_detail", recipe_id=recipe.id))
    prompt=(
        "If possible add things that would make this recipe better(like ingredients or adding better steps or things used)"
        "Rewrite this description in Both Macedonian and English."
        "Keep it friendly and short in both languages. "
        "Do not invent facts in both languages. "
        "Give me directly the description without any other additional things. Text: \n"
        f"{recipe.notes} {recipe.ingredients} {recipe.steps} {recipe.things_used}\n"
    )
    print(prompt)
    result=generate_text(prompt)
    print(result)
    recipe.ai_description = result
    session.commit()
    return redirect(url_for("recipe_detail", recipe_id=recipe.id))

if __name__ == "__main__":
    app.run(debug=True)
