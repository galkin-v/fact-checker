import uvicorn


def main() -> None:
    uvicorn.run("fact_checker.api:app", host="0.0.0.0", port=8080, access_log=False)


if __name__ == "__main__":
    main()
