from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def create_driver(
    headless: bool = False,
    download_dir: Path | None = None,
) -> webdriver.Chrome:
    """
    Crea Chrome WebDriver. Si download_dir se indica, las descargas van ahí sin diálogo.
    """
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")

    if download_dir is not None:
        d = str(download_dir.resolve())

        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": d,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,

                # permitir múltiples descargas automáticas
                "profile.default_content_setting_values.automatic_downloads": 1,
            },
        )

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)