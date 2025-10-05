// Theater Moderator Script
// Two states: active and inactive (default: inactive)
// Listens on channel 8 (config) and channel 0
// Only responds to owner's messages

integer moderator_channel = 8;
integer com_channel = 0;

// State management
integer isActive = 0; // 0 = inactive, 1 = active

// Property reading variables (similar to theater_actor)
string parametersNotecardName = "llm-parameters";
string systemNotecardName = "llm-system"; 
key parametersNotecardQueryId;
key systemNotecardQueryId;
integer parametersCurrentLine = 0;
integer systemCurrentLine = 0;
list systemNotecardLines = [];

// Properties
string charactername;
string model;
string systemInstructions;
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
key modelsValidationId;
key voicesValidationId;
integer modelsValidated = 0;
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
    llHTTPRequest("http://hg.hypergrid.net:7999/aiT/generateAudio", 
        [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], 
        body);
}

// Function to validate model against /models endpoint
validateModel(string modelToValidate)
{
    if (validationInProgress) {
        llOwnerSay("Validation already in progress, please wait...");
        return;
    }
    
    validationInProgress = 1;
    llOwnerSay("Validating model: " + modelToValidate);
    modelsValidationId = llHTTPRequest("http://hg.hypergrid.net:7999/audiomodels", 
        [HTTP_METHOD, "GET", HTTP_MIMETYPE, "application/json"], "");
}

// Function to validate audio parameters against /voices endpoint
validateAudioParameters(string voiceToValidate, string audioModelToValidate)
{
    validationInProgress = 1;
    llOwnerSay("Validating audio voice: " + voiceToValidate + " and audio model: " + audioModelToValidate);
    voicesValidationId = llHTTPRequest("http://hg.hypergrid.net:7999/voices", 
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
    if (model == "" || audio_voice == "" || audio_model == "") {
        llOwnerSay("Error: Some parameters are missing. Cannot validate.");
        return;
    }
    
    llOwnerSay("Starting parameter validation...");
    validateModel(model);
}

// State: INACTIVE (default)
state inactive
{
    state_entry()
    {
        llOwnerSay("Theater Moderator: INACTIVE state");
        llOwnerSay("Use channel " + moderator_channel + " commands to activate:");
        llOwnerSay("  activate - activate moderator");
        llOwnerSay("  status - show current status");
        
        // Initialize property reading
        if (llGetInventoryType(parametersNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + parametersNotecardName + "' not found.");
            return;
        }
        if (llGetInventoryType(systemNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + systemNotecardName + "' not found.");
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
        systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);
        joinkeyNotecardQueryId = llGetNotecardLine(joinkeyNotecardName, 0);
        
        // Listen on moderator channel only
        llListen(moderator_channel, "","","");
    }

    listen(integer channel, string name, key id, string message)
    {
        // Only respond to owner
        if (id != llGetOwner()) {
            return;
        }
        
        if (channel == moderator_channel) {
            if (message == "activate") {
                llOwnerSay("Activating Theater Moderator...");
                llListen(0, "","",""); // Start listening on channel 0
                llStateChange(active);
            }
            else if (message == "status") {
                llOwnerSay("Theater Moderator Status: INACTIVE");
                llOwnerSay("Properties loaded: " + charactername + " | " + model + " | " + audio_voice);
            }
            else {
                llOwnerSay("Unknown command. Available commands: activate, status");
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

                    if (paramName == "charactername") 
                    {
                        charactername = value;
                    }
                    if (paramName == "model") 
                    {
                        model = value;
                    }
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
                llOwnerSay("charactername: " + charactername);
                llOwnerSay("model: " + model);
                llOwnerSay("audio_description: " + audio_description);
                llOwnerSay("audio_voice: " + audio_voice);
                llOwnerSay("audio_model: " + audio_model);
                
                finish_optionstring();
                llOwnerSay("optionstring: " + optionstring);
                
                // Validate parameters
                validateAllParameters();
            }
        }
        
        if (query_id == systemNotecardQueryId)
        {
            if (data != EOF)
            {
                string line = [data];
                systemNotecardLines += line;
                systemCurrentLine++;
                systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);
            }
            else
            {
                string entireContent = llDumpList2String(systemNotecardLines, "\\n");
                llOwnerSay("System notecard content loaded:");
                llOwnerSay("system: " + entireContent);
                systemInstructions = ReplaceQuotesForJson(entireContent);
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
        if (request_id == modelsValidationId) {
            if (status == 200) {
                llOwnerSay("Models validation response received");
                string chatModels = llJsonGetValue(body, ["audio_models"]);
                if (isValueInJsonArray(chatModels, model)) {
                    llOwnerSay("✓ Model '" + model + "' is valid");
                    modelsValidated = 1;
                } else {
                    llOwnerSay("✗ Model '" + model + "' is NOT valid. Available models: " + chatModels);
                    modelsValidated = 0;
                }
                
                if (modelsValidated) {
                    validateAudioParameters(audio_voice, audio_model);
                } else {
                    validationInProgress = 0;
                }
            } else {
                llOwnerSay("Error validating model: HTTP " + (string)status + " - " + body);
                validationInProgress = 0;
            }
            return;
        }
        
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
                
                if (modelsValidated && voicesValidated) {
                    llOwnerSay("✓ All parameters validated successfully!");
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
        llOwnerSay("Theater Moderator: ACTIVE state");
        llOwnerSay("Listening on channels " + moderator_channel + " and 0");
        llOwnerSay("Use channel " + moderator_channel + " commands:");
        llOwnerSay("  deactivate - deactivate moderator");
        llOwnerSay("  status - show current status");
        
        // Listen on both channels
        llListen(moderator_channel, "","","");
        llListen(0, "","","");
    }

    listen(integer channel, string name, key id, string message)
    {
        // Only respond to owner
        if (id != llGetOwner()) {
            return;
        }
        
        if (channel == moderator_channel) {
            if (message == "deactivate") {
                llOwnerSay("Deactivating Theater Moderator...");
                llStateChange(inactive);
            }
            else if (message == "status") {
                llOwnerSay("Theater Moderator Status: ACTIVE");
                llOwnerSay("Properties: " + charactername + " | " + model + " | " + audio_voice);
            }
            else {
                llOwnerSay("Unknown command. Available commands: deactivate, status");
            }
        }
        else if (channel == 0) {
            // Handle public channel messages when active
            llOwnerSay("Moderator received message from " + name + ": " + message);
            
            // Send owner's messages to generateAudio endpoint
            string username = llParseString2List(name, ["@"], [])[0];
            username = llStringTrim(username, 3);
            sendToGenerateAudio(username, message);
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle generateAudio responses
        if(200 == status) {
            llOwnerSay("Audio generation response received:");
            llOwnerSay("Status: " + (string)status);
            llOwnerSay("Response: " + body);
        } else if (202 == status) {
            llOwnerSay("Audio generation in progress...");
        } else if (400 == status) {
            llOwnerSay("Audio generation error: " + body);
        } else if (499 == status) {
            llOwnerSay("Audio generation connection refused, please contact script creator.");
        } else if (422 == status) {
            llOwnerSay("Audio generation unprocessable entity: " + body);
        } else {
            llOwnerSay("Audio generation failed with status: " + (string)status);
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
