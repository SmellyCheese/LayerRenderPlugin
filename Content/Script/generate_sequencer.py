import unreal



#these functions allow you to select predefined or custom behavior 
#all this function also depend of the render_pass
register_and_initialize_track=None
contribute_function=None
visibility_function=None
generate_default_datas=None
set_data_function=None
fill_sequence=None

#variable specific to layer subsystem manager
#environement layer name
environment_layer_name=unreal.StringLibrary.conv_string_to_name("Environment")
#shadow blocker layer name
shadow_blocker_layer_name=unreal.StringLibrary.conv_string_to_name("ShadowBlocker")


#general variable
render_passes=["beauty","depth","shadow"]
sequence={} # working sequence
bind_map={} # map between smc and sequencer binding, for fast iteration




#Layer subsystem local variable
layer_subsystem=None
layers_by_name=[]
shadow_visible_material=None
shadow_invisible_material=None

def init():
    global shadow_visible_material,shadow_invisible_material
    asset_registry=unreal.AssetRegistryHelpers.get_asset_registry()
    invisible_shadow_mat_arr=asset_registry.get_assets_by_package_name("/LayerRenderPlugin/Material/M_Shadow_Invisible")
    if len(invisible_shadow_mat_arr) == 1:
        shadow_invisible_material=invisible_shadow_mat_arr[0].get_asset()
    else:
        unreal.log_error("failed to get the invisible shadow material")
    visible_shadow_mat_arr=asset_registry.get_assets_by_package_name("/LayerRenderPlugin/Material/M_Shadow")
    if len(visible_shadow_mat_arr) == 1:
        shadow_visible_material=visible_shadow_mat_arr[0].get_asset()
    else:
        unreal.log_error("failed to get the visible shadow material")
    actor_components=unreal.EditorLevelLibrary.get_all_level_actors_components()
    for component in actor_components:
        if isinstance(component,unreal.PrimitiveComponent):
            component.set_editor_property("custom_depth_stencil_value",200)
    
def create_sequences(render_pass,package_name,force_clean = False): # create a new sequence from the package path (/Game/Sequence/MyLayerSequence for ex)
    global sequence
    asset_registry=unreal.AssetRegistryHelpers.get_asset_registry()
    data_assets=asset_registry.get_assets_by_package_name(package_name)
    if len(data_assets)==1:
        #a sequencer already exist for this package name. We return it (after cleaning if Force cleaning)
        sequence[render_pass]=data_assets[0].get_asset()
        if force_clean:
            possessables=sequence[render_pass].get_possessables()
            for possessable in possessables:
                possessable.remove()
        return 
    if len(data_assets)==0:
        sequence[render_pass]=unreal.AssetToolsHelpers.get_asset_tools().create_asset(package_name.split("/")[-1], "/"+"/".join(package_name.split("/")[:-1]) , unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
        if sequence[render_pass] is None:
            unreal.log_error("Failed to create a level sequence ")
            quit()
        unreal.log("Creating a new sequence at "+package_name)
        return 
    unreal.log_error("Too many object with this package name: "+package_name)
    exit()

def get_material(smc,slot):
    #in order to avoid adding a another level of complexity, we assume that one StaticMesh has only one material slot
    override_materials=smc.get_editor_property("override_materials")
    if len(override_materials) == 0: # can append after a merge
        mesh=smc.get_editor_property("static_mesh")
        if mesh is None:
            unreal.log_error("we found an empty static mesh component, should not happening. ("+str(smc.get_owner().get_actor_label())+")")
            exit()
        static_material=mesh.get_editor_property("static_materials")
        if len(static_material)==0:
            unreal.log_error("sattic mesh with empty slot material, should not happen")
            exit()
        return static_material[slot].get_editor_property("material_interface")
    return override_materials[slot]
def generate_frame(frame,smc,visible,stencil):
    for current_render_pass in render_passes:
        if smc in bind_map.setdefault(current_render_pass,{}): # no need to create duplicate
            bind=bind_map[current_render_pass][smc]
            for track_number,section_number,channel_number,value in set_data_function()[current_render_pass](visible,stencil):
                bind.get_tracks()[track_number].get_sections()[section_number].get_channels()[channel_number].add_key(unreal.FrameNumber(frame),value)

def set_data_function_layer_system():
    result={}
    #array of {track number,section number,channel number}
    result["beauty"]=lambda visible, stencil : [(0,0,0,not visible),(1,0,0,stencil)]
    result["depth"]=lambda visible , stencil: [(0,0,0,not visible),(1,0,0,stencil)]
    result["shadow"]=lambda visible , stencil: [(0,0,0,not visible),(1,0,0,stencil),(2,0,0,shadow_visible_material)] if (visible) else [(0,0,0,visible),(1,0,0,stencil),(2,0,0,shadow_invisible_material)]
    return result

#special case for material, because the hun
def generate_default_data_shadow_layer_subsystem(smc):
    result=[]
    result.append(("bHiddenInGame",unreal.MovieSceneBoolTrack,True))
    result.append(("bRenderCustomDepth",unreal.MovieSceneBoolTrack,False))

    override_materials=smc.get_editor_property("override_materials")
    if len(override_materials) == 0: # can append after a merge
        mesh=smc.get_editor_property("static_mesh")
        if mesh is None:
            unreal.log_error("we found an empty static mesh component, should not happening. ("+str(smc.get_owner().get_actor_label())+")")
            exit()
        static_materials=mesh.get_editor_property("static_materials")
        if len(static_materials)==0:
            unreal.log_error("static mesh with empty slot material, should not happen")
            exit()
        cpt=0
        for static_material in static_materials:
            result.append(("Element"+str(cpt),unreal.MovieScenePrimitiveMaterialTrack,static_material.get_editor_property("material_interface")))
            cpt+=1
    else:
        cpt=0
        for override_material in override_materials:
            result.append(("Element"+str(cpt),unreal.MovieScenePrimitiveMaterialTrack,override_material))
            cpt+=1
    return result

def generate_default_datas_layer_subsystem():
    result={}
    #beauty pass, we juste modify the stencil and visibility:
    result["beauty"]=lambda smc : [("bHiddenInGame",unreal.MovieSceneBoolTrack,True),("bRenderCustomDepth",unreal.MovieSceneBoolTrack,False)]
    #depth pass, we juste modify the stencil and visibility:
    result["depth"]=lambda smc : [("bHiddenInGame",unreal.MovieSceneBoolTrack,True),("bRenderCustomDepth",unreal.MovieSceneBoolTrack,False)]
    #shadow pass, we juste modify the stencil and visibility and switching material:
    result["shadow"]=generate_default_data_shadow_layer_subsystem
    return result
#this function setup the sequence by filling all smc available in the layer and generate the first frame thanks to datas
#datas is supposed to be an array of tuple (propertyName, propertytracktype, default_value)
#default value can be a function that take the smc as input or variable
def register_and_initialize_track_layer_subsystem(datas):
    unreal.log("registering layer subsystem into sequence")
    global layer_subsystem
    global layers_by_name
    layer_subsystem = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    if layer_subsystem is None:
        unreal.log_error("Failed to get the layer subsystem")
        exit()
    layers_by_name=layer_subsystem.add_all_layer_names_to()
    for layer in layers_by_name:
        actors=layer_subsystem.get_actors_from_layer(layer)
        for actor in actors:
            smcs=actor.get_components_by_class(unreal.StaticMeshComponent)
            for smc in smcs:
                for current_render_pass in render_passes:
                    if smc in bind_map.setdefault(current_render_pass,{}): # no need to create duplicate
                        continue
                    bind=sequence[current_render_pass].add_possessable(smc)
                    bind_map[current_render_pass][smc]=bind
                    for data in datas[current_render_pass](smc):
                        property_name,property_track_type,default_value=data
                        current_track=bind.add_track(property_track_type)
                        current_track.set_property_name_and_path(property_name,property_name)
                        current_section=current_track.add_section()
                        current_section.set_start_frame(0)
                        current_section.set_end_frame(len(layers_by_name)+1)
                        first_channel=current_section.get_channels()[0]
                        if callable(default_value):
                            first_channel.add_key(unreal.FrameNumber(0),default_value(smc))
                        else:
                            first_channel.add_key(unreal.FrameNumber(0),default_value)
def fill_sequence_layer_subsystem():
    previous_layer_smc=[]
    frame=1
    for layer in layers_by_name:
        #skipping environement and shadow blocker layer
        if layer == environment_layer_name:
            continue
        if layer == shadow_blocker_layer_name:
            continue
        
        frame+=1
        actors=layer_subsystem.get_actors_from_layer(layer)
        #restoring previous SMC
        for smc in previous_layer_smc :
            generate_frame(frame,smc,False,False)
        #setting new SMC
        previous_layer_smc=[]
        #setting actor from current layer
        for actor in actors:
            smcs=actor.get_components_by_class(unreal.StaticMeshComponent)
            for smc in smcs:
                generate_frame(frame,smc,True,True)
                previous_layer_smc.append(smc)
        actors=layer_subsystem.get_actors_from_layer(environment_layer_name)
        #setting actor from environment (if we are sure that environment intesection with other layer is null, we could avoid this step)
        for actor in actors:
            smcs=actor.get_components_by_class(unreal.StaticMeshComponent)
            for smc in smcs:
                generate_frame(frame,smc,True,False)
                previous_layer_smc.append(smc)
        #setting actor from ShadowBlocker (if we are sure that shadowblocker intesection with other layer is null, we could avoid this step)
        actors=layer_subsystem.get_actors_from_layer(shadow_blocker_layer_name)
        for actor in actors:
            smcs=actor.get_components_by_class(unreal.StaticMeshComponent)
            for smc in smcs:
                generate_frame(frame,smc,True,False)
                previous_layer_smc.append(smc)
        
        
        



                        
            



def registering_layer_subsystem_logic_function():
    global generate_default_datas,register_and_initialize_track,fill_sequence,set_data_function
    generate_default_datas=generate_default_datas_layer_subsystem
    register_and_initialize_track=register_and_initialize_track_layer_subsystem
    fill_sequence=fill_sequence_layer_subsystem
    set_data_function=set_data_function_layer_system


def run():
    init()
    #we are registering function specific to the layer subsystem logic
    registering_layer_subsystem_logic_function()
    #we are creating the output assets:
    for current_render_pass in render_passes:
        create_sequences(current_render_pass,"/Game/output_sequence/seq_"+current_render_pass,True)
    # generating tracks,section,channel,default value for properties in sequencer.It depends of the way you want to render the layers
    data_for_seq_initialisation=generate_default_datas()
    #init of the sequences, It depends of the logic, :
    register_and_initialize_track(data_for_seq_initialisation)
    #We have a sequence and the first frame, the init one is done:
    #now we will iterate on all layer to fill the sequence, with 1 layer = 1 frame
    fill_sequence()



    

run()




