
from dynaconf import Dynaconf



settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=['settings.toml', '.secrets.toml'],
    environments=True,
    load_dotenv=True,
    CORRELATION_ID_LENGTH=25
)