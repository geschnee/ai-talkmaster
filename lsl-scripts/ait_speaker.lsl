// Speaker Script
// Two states: active and inactive (default: inactive)
// Listens on channel 8 (config) and channel 0
// Only responds to owner's messages
// When active the speakers messages get forwarded to AI Talkmaster and are voiced for the audio stream.
// There is no large language model text response for the sent messages!

// This script is intended to be used on a (HUD) wearable object.


integer command_channel = 8;

// State management
integer isActive = 0; // 0 = inactive, 1 = active

string ait_endpoint = "http://hg.hypergrid.net:6000";

// Visual feedback colors
vector inactiveColor = <0.2, 0.2, 0.2>; // Dark gray for inactive
vector activeColor = <1.0, 1.0, 1.0>;   // Bright white for active

// Property reading variables (similar to theater_actor)
string parametersNotecardName = "speaker-parameters";
key parametersNotecardQueryId;
integer parametersCurrentLine = 0;

// Properties
string audio_instructions;
string audio_voice;
string audio_model;

// Option string handling
string optionstring;
list optionStringParts=[];

list optionParameters = [
    "num_ctx", "repeat_last_n","repeat_penalty","temperature","seed","stop","num_predict","top_k","top_p","min_p"
];

// Join key
string joinkeyNotecardName = "join_key";
key joinkeyNotecardQueryId;
string join_key;

// Validation variables
key voicesValidationId;
key startConversationId;
integer voicesValidated = 0;
integer validationInProgress = 0;
integer validatingForActivation = 0;

// Notecard completion tracking
integer notecardsCompleted = 0;
integer PARAMETERS_NOTECARD_COMPLETED = 1;
integer JOINKEY_NOTECARD_COMPLETED = 2;
integer ALL_NOTECARDS_COMPLETED = 3; // 1 + 2 = 3

// HTTP response handling
integer max_response_length = 16384;

// Audio generation variables
string audioGenerationMessageId;

// Function to split text into chunks
list splitText(string text)
{
    list chunks = [];
    integer textLength = llStringLength(text);
    
    // If text is already short enough, return it as a single chunk
    if (textLength <= 1024)
    {
        return [text];
    }
    
    integer currentPos = 0;
    
    while (currentPos < textLength)
    {
        integer endPos = currentPos + 1024;
        
        // Make sure we don't go beyond the text length
        if (endPos > textLength)
        {
            endPos = textLength;
        }
        
        // If we're not at the end of the text, try to find a natural breaking point
        if (endPos < textLength)
        {
            // First try to break at a newline
            integer newlinePos = -1;
            integer i;
            
            // Find the rightmost newline in our range
            for (i = endPos - 1; i >= currentPos; --i)
            {
                if (newlinePos==-1 && llGetSubString(text, i, i) == "\n")
                {
                    newlinePos = i;
                }
            }
            
            if (newlinePos != -1)
            {
                // Found a newline, break there (include the newline in the chunk)
                endPos = newlinePos + 1;
            }
            else
            {
                // No newline found, try to break at a space
                integer spacePos = -1;
                
                // Find the rightmost space in our range
                for (i = endPos - 1; i >= currentPos; --i)
                {
                    if (spacePos == -1 && llGetSubString(text, i, i) == " ")
                    {
                        spacePos = i;
                    }
                }
                
                if (spacePos != -1)
                {
                    // Found a space, break there (include the space in the chunk)
                    endPos = spacePos + 1;
                }
            }
        }
        
        // Add the chunk to our list
        chunks += [llGetSubString(text, currentPos, endPos - 1)];
        currentPos = endPos;
    }
    
    return chunks;
}

start_optionstring() {
    optionstring = "{";
    optionStringParts = [];
}

add_option(string optionname, string value){
    if (optionname == "stop"){
        optionStringParts = optionStringParts + ["\"stop\": [\"" + value + "\"]"];
    } else {
        optionStringParts = optionStringParts + ["\""+optionname+"\": " + value];
    }
}

finish_optionstring(){
    string joins = llDumpList2String(optionStringParts, ", ");
    optionstring = "{ " + joins +" }";
}

string ReplaceQuotesForJson(string input)
{
    // Split on "
    list parts = llParseString2List(input, ["\""], []);
    // Join back with replacement
    return llDumpList2String(parts, "\\\"");
}

// Function to send message to generateAudio endpoint
ait_generateAudio(string username, string message)
{
    audioGenerationMessageId = (string) llGenerateKey();

    string jsonBody = llList2Json(JSON_OBJECT, ["join_key", join_key, "username", username, "message", message, "audio_instructions", audio_instructions, "audio_voice", audio_voice, "audio_model", audio_model]);

    llHTTPRequest(ait_endpoint + "/ait/generateAudio", 
        [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], 
        jsonBody);
}

validateAudioParameters(string voiceToValidate, string audioModelToValidate, integer forActivation)
{
    if (validationInProgress) {
        llOwnerSay("Validation already in progress, please wait...");
        return;
    }
    
    validationInProgress = 1;
    validatingForActivation = forActivation;
    
    if (forActivation) {
        llOwnerSay("Validating audio parameters for activation: " + voiceToValidate + " and audio model: " + audioModelToValidate);
    } else {
        llOwnerSay("Validating audio voice: " + voiceToValidate + " and audio model: " + audioModelToValidate);
    }
    
    voicesValidationId = llHTTPRequest(ait_endpoint + "/audio_models", 
        [HTTP_METHOD, "GET", HTTP_MIMETYPE, "application/json"], "");
}

// Function to check if a value exists in a JSON array
integer isValueInJsonArray(string jsonString, string value)
{
    // Simple check for the value in the JSON string
    if (llSubStringIndex(jsonString, "\"" + value + "\"") != -1) {
        return TRUE;
    }
    return FALSE;
}

start_conversation(){
    string jsonBody = llList2Json(JSON_OBJECT, ["join_key", join_key]);

    startConversationId=llHTTPRequest(ait_endpoint + "/ait/startConversation", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
}

// Function to validate all parameters after they are loaded
validateAllParameters()
{
    if (audio_voice == "" || audio_model == "") {
        llOwnerSay("Error: Some parameters are missing. Cannot validate.");
        return;
    }
    
    llOwnerSay("Starting parameter validation...");
    validateAudioParameters(audio_voice, audio_model, 0);
}

// Default state - automatically switch to inactive
default
{
    state_entry()
    {
        llOwnerSay("AIT Speaker: Initializing...");
        state inactive;
    }
}

// State: INACTIVE
state inactive
{
    state_entry()
    {
        llOwnerSay("AIT Speaker: INACTIVE state");
        llOwnerSay("Use channel " + command_channel + " or click the object for changing the state");
        
        // Set visual state to inactive
        isActive = 0;
        updateVisualState();
        
        // Initialize property reading
        if (llGetInventoryType(parametersNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + parametersNotecardName + "' not found. Please add it to the object.");
            return;
        }
        if (llGetInventoryType(joinkeyNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + joinkeyNotecardName + "' not found. Please add it to the object.");
            return;
        }
        
        // Start reading notecards
        start_optionstring();
        parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
        joinkeyNotecardQueryId = llGetNotecardLine(joinkeyNotecardName, 0);
        
        // Listen on config channel
        llListen(command_channel, "","","");
    }

    listen(integer channel, string name, key id, string message)
    {
        // Only respond to owner
        if (id != llGetOwner()) {
            return;
        }
        
        if (channel == command_channel) {
            // Handle dialog responses
            if (message == "ActivateSpeaker") {
                llOwnerSay("Activating AIT Speaker...");
                // Validate audio parameters before activation
                if (audio_voice == "" || audio_model == "") {
                    llOwnerSay("Error: Audio parameters not loaded. Cannot activate speaker.");
                    return;
                }
                validateAudioParameters(audio_voice, audio_model, 1);
            }
            else if (message == "status") {
                llOwnerSay("AIT Speaker Status: INACTIVE");
                llOwnerSay("Properties loaded: " + audio_voice + " | " + audio_model);
            }
            else if (message == "Close") {
                llOwnerSay("Dialog closed.");
            }
        }
    }

    dataserver(key query_id, string data)
    {
        if (query_id == parametersNotecardQueryId)
        {
            if (data != EOF)
            {
                string line = [data];
                list splits = llParseString2List(line, [":"],[]);
                
                if ( llGetListLength(splits) == 2 ) 
                {
                    string paramName = llList2String(splits, 0);
                    string value = llList2String(splits, 1);

                    if (paramName == "audio_voice") 
                    {
                        audio_voice = value;
                    }
                    if (paramName == "audio_model") 
                    {
                        audio_model = value;
                    }
                    if (paramName == "audio_instructions") 
                    {
                        audio_instructions = value;
                    }
                    
                    integer listLength = llGetListLength(optionParameters);
                    integer i;
                    for (i=0; i< listLength; i++)
                    {
                        string indexName = llList2String(optionParameters, i);
                        if (paramName == indexName) 
                        {
                            add_option(paramName, value);
                        }
                    }
                }
                // Get the next line
                parametersCurrentLine++;
                parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
            }
            else
            {
                // Parameters loaded
                llOwnerSay("Parameters loaded:");
                llOwnerSay("audio_instructions: " + audio_instructions);
                llOwnerSay("audio_voice: " + audio_voice);
                llOwnerSay("audio_model: " + audio_model);
                
                finish_optionstring();
                llOwnerSay("optionstring: " + optionstring);
                
                notecardsCompleted = notecardsCompleted | PARAMETERS_NOTECARD_COMPLETED;
                
                // Check if all notecards are completed
                if (notecardsCompleted == ALL_NOTECARDS_COMPLETED) {
                    validateAllParameters();
                }
            }
        }
        
        
        if (query_id == joinkeyNotecardQueryId)
        {
            if (data != EOF)
            {
                string line = [data];
                join_key = line;
                llOwnerSay("join_key has been read " + join_key);
                
                notecardsCompleted = notecardsCompleted | JOINKEY_NOTECARD_COMPLETED;
                
                // Check if all notecards are completed
                if (notecardsCompleted == ALL_NOTECARDS_COMPLETED) {
                    validateAllParameters();
                }
            }
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == voicesValidationId) {
            if (status == 200) {
                
                string validVoices = llJsonGetValue(body, ["allowed_voices"]);
                string audioModels = llJsonGetValue(body, ["audio_models"]);
                
                integer voiceValid = isValueInJsonArray(validVoices, audio_voice);
                integer audioModelValid = isValueInJsonArray(audioModels, audio_model);
                
                if (voiceValid) {
                    llOwnerSay("✓ Audio voice '" + audio_voice + "' is valid");
                } else {
                    llOwnerSay("✗ Audio voice '" + audio_voice + "' is NOT valid. Available voices: " + validVoices);
                }
                
                if (audioModelValid) {
                    llOwnerSay("✓ Audio model '" + audio_model + "' is valid");
                } else {
                    llOwnerSay("✗ Audio model '" + audio_model + "' is NOT valid. Available audio models: " + audioModels);
                }
                
                voicesValidated = (voiceValid && audioModelValid) ? 1 : 0;
                
                // Check if this is activation validation
                if (validatingForActivation) {
                    if (voicesValidated) {
                        llOwnerSay("✓ Activation validation successful! Switching to active state.");
                        isActive = 1; // Set active state
                        updateVisualState(); // Update visual appearance
                        llListen(0, "","",""); // Start listening on channel 0
                        validatingForActivation = 0;
                        validationInProgress = 0;
                        state active;
                    } else {
                        llOwnerSay("✗ Activation validation failed. Speaker remains inactive.");
                        llOwnerSay("Please check your audio configuration and try again.");
                        validatingForActivation = 0;
                        validationInProgress = 0;
                    }
                } else {
                    // Regular validation (during initialization)
                    if (voicesValidated) {
                        llOwnerSay("✓ All parameters validated successfully!");
                        start_conversation();
                        // Show dialog after successful validation
                        showDialog(llGetOwner());
                    } else {
                        llOwnerSay("✗ Parameter validation failed. Please check your configuration.");
                    }
                    validationInProgress = 0;
                }
            } else {
                llOwnerSay("Error validating audio parameters: HTTP " + (string)status + " - " + body);
                if (validatingForActivation) {
                    llOwnerSay("✗ Activation validation failed due to server error. Speaker remains inactive.");
                    validatingForActivation = 0;
                }
                validationInProgress = 0;
            }
            return;
        }

        if (request_id == startConversationId) {
            llOwnerSay(body);
            return;
        }
    }

    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        if (toucher == llGetOwner()) {
            showDialog(toucher);
        }
    }

    // If changes are done to object inventory then reset the script.
    changed(integer a)
    {
        if(a & CHANGED_INVENTORY ) {
            llResetScript();
        }
    }
}

// State: ACTIVE
state active
{
    state_entry()
    {
        llOwnerSay("AIT Speaker: ACTIVE state");
        llOwnerSay("Will forward your messages on channel 0 to AIT and turn it into voice");
        llOwnerSay("Use channel " + command_channel + " or click the object for changing the state");
        
        // Set visual state to active
        isActive = 1;
        updateVisualState();
        
        // Listen on all channels
        llListen(command_channel, "","","");
        llListen(0, "","","");
    }

    listen(integer channel, string name, key id, string message)
    {
        // Only respond to owner
        if (id != llGetOwner()) {
            return;
        }
        
        if (channel == command_channel) {
            // Handle dialog responses
            if (message == "DeactivateSpeaker") {
                llOwnerSay("Deactivating AIT Speaker...");
                isActive = 0; // Set inactive state
                updateVisualState(); // Update visual appearance
                state inactive;
            }
            else if (message == "status") {
                llOwnerSay("AIT Speaker Status: ACTIVE");
                llOwnerSay("Properties: " + audio_voice + " | " + audio_model);
            }
            else if (message == "Close") {
                llOwnerSay("Dialog closed.");
            }
        }
        else if (channel == 0) {
            // Handle public channel messages when active
            
            // Only send to generateAudio when state is active
            if (isActive == 1) {
                // Send owner's messages to generateAudio endpoint
                string username = llParseString2List(name, ["@"], [])[0];
                username = llStringTrim(username, 3);
                ait_generateAudio(username, message);
            } else {
                llOwnerSay("Speaker is not active, ignoring message");
            }
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle generateAudio responses
        if(200 == status) {
            llOwnerSay("Audio generated successfully");
        } else {
            // Report all other status codes to owner
            llOwnerSay("HTTP Error " + (string)status + ": " + body);
        }
    }

    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        if (toucher == llGetOwner()) {
            showDialog(toucher);
        }
    }

    // If changes are done to object inventory then reset the script.
    changed(integer a)
    {
        if(a & CHANGED_INVENTORY ) {
            llResetScript();
        }
    }
}

// Function to update visual appearance based on state
updateVisualState()
{
    if (isActive == 1) {
        // Active state - bright and glowing
        llSetColor(activeColor, ALL_SIDES);
        llSetPrimitiveParams([PRIM_FULLBRIGHT, ALL_SIDES, TRUE]);
    } else {
        // Inactive state - dark and dim
        llSetColor(inactiveColor, ALL_SIDES);
        llSetPrimitiveParams([PRIM_FULLBRIGHT, ALL_SIDES, FALSE]);
    }
}

// Function to show dialog based on current state
showDialog(key user)
{
    if (isActive == 1) {
        // Active state dialog
        llDialog(user, 
            "AIT Speaker - ACTIVE\n\nProperties:\nvoice: " + audio_voice + "\naudio model: " + audio_model + "\n\n",
            ["DeactivateSpeaker", "Close"], 
            command_channel);
    } else {
        // Inactive state dialog
        llDialog(user, 
            "AIT Speaker - INACTIVE\n\nProperties:\nvoice: " + audio_voice + "\naudio model: " + audio_model + "\n\nPress activate to forward your chat messages on channel 0 to AIT audio stream.",
            ["ActivateSpeaker", "Close"], 
            command_channel);
    }
}
