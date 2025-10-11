// Speaker Script
// Two states: active and inactive (default: inactive)
// Listens on channel 8 (config) and channel 0
// Only responds to owner's messages
// When active the speakers messages get forwarded to AI Talkmaster and are simply voiced for the audio stream.


integer configChannel = 8;
integer com_channel = 0;

// State management
integer isActive = 0; // 0 = inactive, 1 = active

string ait_endpoint = "http://hg.hypergrid.net:7999";

// Visual feedback colors
vector inactiveColor = <0.2, 0.2, 0.2>; // Dark gray for inactive
vector activeColor = <1.0, 1.0, 1.0>;   // Bright white for active

// Property reading variables (similar to theater_actor)
string parametersNotecardName = "speaker-parameters";
key parametersNotecardQueryId;
integer parametersCurrentLine = 0;

// Properties
string audio_description;
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
integer voicesValidated = 0;
integer validationInProgress = 0;

// HTTP response handling
integer max_response_length = 16384;

// Audio generation variables
integer audioGenerationQueue = 0;
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

string deleteUpToSubstring(string input, string substring)
{
    integer position = llSubStringIndex(input, substring);
    
    if (position == -1) // Substring not found
        return input;
    
    return llDeleteSubString(input, 0, position + llStringLength(substring) - 1);
}

string ReplaceQuotesForJson(string input)
{
    // Split on "
    list parts = llParseString2List(input, ["\""], []);
    // Join back with replacement
    return llDumpList2String(parts, "\\\"");
}

// Function to send message to generateAudio endpoint
sendToGenerateAudio(string username, string message)
{
    audioGenerationQueue += 1;
    audioGenerationMessageId = "moderator_" + username +"_"+ (string)audioGenerationQueue;
    
    string body = "{
        \"join_key\": \""+join_key+"\",
        \"username\": \""+username+"\",
        \"message\": \""+ReplaceQuotesForJson(message)+"\",
        \"message_id\": \""+audioGenerationMessageId+ "\",
        \"audio_description\": \"" + audio_description + "\",
        \"audio_voice\": \""+ audio_voice + "\",
        \"audio_model\": \"" + audio_model + "\" 
    }";
    
    llOwnerSay("Sending message to generateAudio: " + message);
    llHTTPRequest(ait_endpoint + "/ait/generateAudio", 
        [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], 
        body);
}


// Function to validate audio parameters against /voices endpoint
validateAudioParameters(string voiceToValidate, string audioModelToValidate)
{
    validationInProgress = 1;
    llOwnerSay("Validating audio voice: " + voiceToValidate + " and audio model: " + audioModelToValidate);
    voicesValidationId = llHTTPRequest(ait_endpoint + "/voices", 
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

// Function to validate all parameters after they are loaded
validateAllParameters()
{
    if (audio_voice == "" || audio_model == "") {
        llOwnerSay("Error: Some parameters are missing. Cannot validate.");
        return;
    }
    
    llOwnerSay("Starting parameter validation...");
    validateAudioParameters(audio_voice, audio_model);
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
        llOwnerSay("Use channel " + configChannel + " or click the object for changing the state");
        
        // Set visual state to inactive
        isActive = 0;
        updateVisualState();
        
        // Initialize property reading
        if (llGetInventoryType(parametersNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + parametersNotecardName + "' not found.");
            return;
        }
        if (llGetInventoryType(joinkeyNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + joinkeyNotecardName + "' not found.");
            return;
        }
        
        // Start reading notecards
        start_optionstring();
        parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
        joinkeyNotecardQueryId = llGetNotecardLine(joinkeyNotecardName, 0);
        
        // Listen on config channel
        llListen(configChannel, "","","");
    }

    listen(integer channel, string name, key id, string message)
    {
        // Only respond to owner
        if (id != llGetOwner()) {
            return;
        }
        
        if (channel == configChannel) {
            // Handle dialog responses
            if (message == "ActivateSpeaker") {
                llOwnerSay("Activating AIT Speaker...");
                isActive = 1; // Set active state
                updateVisualState(); // Update visual appearance
                llListen(0, "","",""); // Start listening on channel 0
                state active;
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
                    if (paramName == "audio_description") 
                    {
                        audio_description = value;
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
                llOwnerSay("audio_description: " + audio_description);
                llOwnerSay("audio_voice: " + audio_voice);
                llOwnerSay("audio_model: " + audio_model);
                
                finish_optionstring();
                llOwnerSay("optionstring: " + optionstring);
                
                // Validate parameters
                validateAllParameters();
            }
        }
        
        
        if (query_id == joinkeyNotecardQueryId)
        {
            if (data != EOF)
            {
                string line = [data];
                join_key = line;
                llOwnerSay("join_key has been read " + join_key);
            }
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == voicesValidationId) {
            if (status == 200) {
                llOwnerSay("Voices validation response received");
                string validVoices = llJsonGetValue(body, ["valid_voices"]);
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
                
                if (voicesValidated) {
                    llOwnerSay("✓ All parameters validated successfully!");
                    // Show dialog after successful validation
                    showDialog(llGetOwner());
                } else {
                    llOwnerSay("✗ Parameter validation failed. Please check your configuration.");
                }
                
                validationInProgress = 0;
            } else {
                llOwnerSay("Error validating audio parameters: HTTP " + (string)status + " - " + body);
                validationInProgress = 0;
            }
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
        llOwnerSay("Use channel " + configChannel + " or click the object for changing the state");
        
        // Set visual state to active
        isActive = 1;
        updateVisualState();
        
        // Listen on all channels
        llListen(configChannel, "","","");
        llListen(0, "","","");
    }

    listen(integer channel, string name, key id, string message)
    {
        // Only respond to owner
        if (id != llGetOwner()) {
            return;
        }
        
        if (channel == configChannel) {
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
            llOwnerSay("Speaker received message from " + name + ": " + message);
            
            // Only send to generateAudio when state is active
            if (isActive == 1) {
                // Send owner's messages to generateAudio endpoint
                string username = llParseString2List(name, ["@"], [])[0];
                username = llStringTrim(username, 3);
                sendToGenerateAudio(username, message);
            } else {
                llOwnerSay("Speaker is not active, ignoring message");
            }
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle generateAudio responses
        if(200 == status) {
            llOwnerSay("Audio generation response received:");
            llOwnerSay("Status: " + (string)status);
            llOwnerSay("Response: " + body);
        } else if (425 == status) {
            // 425 means the response is not yet available from AI talkmaster
            return;
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
            configChannel);
    } else {
        // Inactive state dialog
        llDialog(user, 
            "AIT Speaker - INACTIVE\n\nProperties:\nvoice: " + audio_voice + "\naudio model: " + audio_model + "\n\nPress activate to forward your chat messages on channel 0 to AIT audio stream.",
            ["ActivateSpeaker", "Close"], 
            configChannel);
    }
}
