import sys

if len(sys.argv) > 1 and sys.argv[1] == "install-chrome":
    from . import install

    if "--list" in sys.argv:
        install.list_browsers()
        sys.exit(0)

    if "--browser" in sys.argv:
        idx = sys.argv.index("--browser")
        if idx + 1 < len(sys.argv):
            browsers = sys.argv[idx + 1].split(",")
            install.install_chrome(browser_names=browsers)
        else:
            print("Error: --browser requires a value (e.g. --browser chrome,brave)")
            sys.exit(1)
    else:
        install.install_chrome()
else:
    from . import main
    main.main()
