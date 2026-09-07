from sqlalchemy import inspect, text

from app.core.database import engine


def add_column_if_missing(
    connection,
    inspector,
    table_name,
    column_name,
    column_definition,
):
    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    if column_name in columns:
        print(
            f"✓ {table_name}.{column_name} already exists"
        )
        return

    connection.execute(
        text(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} "
            f"{column_definition}"
        )
    )

    print(
        f"✓ Added {table_name}.{column_name}"
    )


def main():
    print("Checking FinWise database...")
    print()

    with engine.begin() as connection:

        inspector = inspect(connection)

        # -------------------------------------------------
        # Make sure budgets table exists
        # -------------------------------------------------

        if not inspector.has_table("budgets"):
            print("ERROR: budgets table was not found.")
            return

        # -------------------------------------------------
        # Add budget name
        # -------------------------------------------------

        add_column_if_missing(
            connection,
            inspector,
            "budgets",
            "name",
            "VARCHAR(100) NOT NULL DEFAULT 'Monthly Budget'",
        )

        # Refresh inspector after schema change
        inspector = inspect(connection)

        # -------------------------------------------------
        # Add priority
        # -------------------------------------------------

        add_column_if_missing(
            connection,
            inspector,
            "budgets",
            "priority",
            "VARCHAR(20) NOT NULL DEFAULT 'medium'",
        )

        # Refresh inspector again
        inspector = inspect(connection)

        # -------------------------------------------------
        # Add planning day
        # -------------------------------------------------

        add_column_if_missing(
            connection,
            inspector,
            "budgets",
            "planning_day",
            "INT NOT NULL DEFAULT 1",
        )

    print()
    print("======================================")
    print("Budget database update completed.")
    print("======================================")


if __name__ == "__main__":
    main()