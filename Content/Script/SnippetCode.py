import unreal

# how to get metadatas of an actor  from datasmith:
specific_tag=unreal.DatasmithContentLibrary.get_datasmith_user_data_value_for_key(my_actor,"metadata_key")

#get all object with metadata with specific key:
tuple=unreal.DatasmithContentLibrary.get_all_objects_and_values_for_key("metadata_key",unreal.Actor)
tuple[0] # array of actor
tuple[1] # value

# get all asset under specific path:
asset_registry=unreal.AssetRegistryHelpers.get_asset_registry()
asset_in_path=asset_registry.get_assets_by_path("/Game/PathToSearch/",recursive=True)