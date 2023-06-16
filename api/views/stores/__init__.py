from fastapi import APIRouter, Security
import json

from api import crud, models, schemes, utils
from api.views.stores.integrations import router as integrations_router

router = APIRouter()


@router.get("/{model_id}/ping")
async def ping_email(
    model_id: str,
    user: models.User = Security(utils.authorization.auth_dependency, scopes=["store_management"]),
):
    model = await utils.database.get_object(models.Store, model_id, user)
    return utils.email.check_ping(
        model.email_host,
        model.email_port,
        model.email_user,
        model.email_password,
        model.email,
        model.email_use_ssl,
    )


# NOTE: to_optional not required here because settings have default values set everywhere
@router.patch("/{model_id}/checkout_settings", response_model=schemes.Store)
async def set_store_checkout_settings(
    model_id: str,
    settings: schemes.StoreCheckoutSettings,
    user: models.User = Security(utils.authorization.auth_dependency, scopes=["store_management"]),
):
    model = await utils.database.get_object(models.Store, model_id, user)
    await model.set_json_key("checkout_settings", settings)
    return model


@router.patch("/{model_id}/theme_settings", response_model=schemes.Store)
async def set_store_theme_settings(
    model_id: str,
    settings: schemes.StoreThemeSettings,
    user: models.User = Security(utils.authorization.auth_dependency, scopes=["store_management"]),
):
    model = await utils.database.get_object(models.Store, model_id, user)
    await model.set_json_key("theme_settings", settings)
    return model


@router.patch("/{model_id}/plugin_settings", response_model=schemes.Store)
async def set_store_plugin_settings(
    model_id: str,
    settings: schemes.StorePluginSettings,
    user: models.User = Security(utils.authorization.auth_dependency, scopes=["store_management"]),
):
    model = await utils.database.get_object(models.Store, model_id, user)
    await model.set_json_key("plugin_settings", settings)
    return model

@router.patch("/{model_id}/metadata", response_model=schemes.Store)
async def set_store_metadata_settings(
    model_id: str,
    settings: schemes.StoreMetadataSettings,
    user: models.User = Security(utils.authorization.auth_dependency, scopes=["store_management"]),
):
    model = await utils.database.get_object(models.Store, model_id, user)

    # Update the metadata with the new settings
    metadata = model.metadata or {}
    metadata.update(settings.dict())

    # Save the updated metadata to the model
    model.metadata = metadata
   
    kwargs = {"metadata": metadata}
    await model.update(**kwargs).apply()

    return model



utils.routing.ModelView.register(
    router,
    "/",
    models.Store,
    schemes.Store,
    schemes.CreateStore,
    custom_methods={
        "post": crud.stores.create_store,
        "get_one": crud.stores.get_store,
    },
    get_one_model=None,
    get_one_auth=False,
    scopes=["store_management"],
)


router.include_router(integrations_router, prefix="/{store_id}/integrations")
