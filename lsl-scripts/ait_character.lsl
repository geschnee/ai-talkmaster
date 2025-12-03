// This script is used to define a character for AI Talkmaster conversations.
// The script can be in state active and inactive.
// When active it listens to messages that mention the character's name.
// When it's name is mentioned by a user or character, it sends a request to the AI Talkmaster and waits for the generated response, which is then said by the character.
// More details at https://github.com/geschnee/ai-talkmaster

integer command_channel = 8;

integer com_channel = 0;
integer listener_public_channel;
string prompt;
key user=NULL_KEY;
string username ="";
float reserveTime = 180.0;
float pollFreq = 2.0;
float stopwatch;

string ait_endpoint = "https://hg.hypergrid.net:6000";


float conversation_time=0;
integer pollingForResponse=0;
float polling_start_time = 0.0;
float polling_timeout = 300.0; // Stop polling after 5 minutes

integer max_response_length = 16384;


float CONVERSATION_INCREMENT=60;

integer MAX_LENGTH = 1024;    // Maximum string length in LSL



// Read Entire Notecard as Single String
string parametersNotecardName = "llm-parameters";
string systemNotecardName = "llm-system"; 
key parametersNotecardQueryId;
key systemNotecardQueryId;
integer parametersCurrentLine = 0;
integer systemCurrentLine = 0;
list systemNotecardLines = [];


string charactername="";
string model="";
string systemInstructions;
string audio_instructions;
string audio_voice="";
string audio_model="";

list optionParameters_stringlist = ["stop"];
list optionParameters_integers = ["num_ctx","repeat_last_n", "seed", "num_predict", "top_k"];
list optionParameters_floats = ["repeat_penalty","temperature","top_p","min_p"];

// List to store option key-value pairs
list optionsList = [];



string joinkeyNotecardName = "join_key";
key joinkeyNotecardQueryId;
string join_key = "";

// Validation variables
key modelsValidationId;
key voicesValidationId;
key startConversationId;
key getMessageResponseId;
key postMessageId;

integer modelsValidated = 0;
integer audioIsValidated = 0;
integer fullyValidated = 0;

integer isActive = 0;

string pollingMessageId;

// Function to print response text, splitting into chunks if necessary
printResponse(string response) {
    integer textLength = llStringLength(response);
    list chunks = [];
    
    // If text is already short enough, print it directly
    if (textLength <= MAX_LENGTH)
    {
        llSay(0, response);
        return;
    }
    
    integer currentPos = 0;
    
    while (currentPos < textLength)
    {
        integer endPos = currentPos + MAX_LENGTH;
        
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
                if (newlinePos==-1 && llGetSubString(response, i, i) == "\n")
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
                    if (spacePos == -1 && llGetSubString(response, i, i) == " ")
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
        chunks += [llGetSubString(response, currentPos, endPos - 1)];
        currentPos = endPos;
    }
    
    // Print all chunks with numbering
    integer j;
    for (j = 0; j < llGetListLength(chunks); ++j)
    {
        string chunk = llList2String(chunks, j);
        integer j_plus = j + 1;
        llSay(0, j_plus + " " + chunk);
    }
}

add_stringlist_option(string optionname, string value) {
    optionsList += [optionname, llList2Json(JSON_ARRAY, [value])];
}

add_int_option(string optionname, integer num) {
    optionsList += [optionname, num];
}

add_float_option(string optionname, float num) {
    optionsList += [optionname, num];
}

// Add option with automatic type detection
add_option(string optionname, string value) {
    // Check which type list contains this parameter
    if (llListFindList(optionParameters_stringlist, [optionname]) != -1) {
        add_stringlist_option(optionname, value);
    } else if (llListFindList(optionParameters_integers, [optionname]) != -1) {
        integer intValue = (integer)value;
        add_int_option(optionname, intValue);
    } else if (llListFindList(optionParameters_floats, [optionname]) != -1) {
        float floatValue = (float)value;
        add_float_option(optionname, floatValue);
    } else {
        llOwnerSay("Unknown option: " + optionname);
    }
}


ait_postMessage(string message_id, string username, string message) {
    string optionstring = llList2Json(JSON_OBJECT, optionsList);
    string jsonBody = llList2Json(JSON_OBJECT, ["join_key", join_key, "username", username, "message", message, "model", model,"system_instructions", systemInstructions, "charactername", charactername, "message_id", message_id, "options", optionstring, "audio_instructions", audio_instructions, "audio_voice", audio_voice, "audio_model", audio_model]);

    postMessageId = llHTTPRequest(ait_endpoint + "/ait/postMessage", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
}

ait_getMessageResponse(string message_id) {
    string uriParams = "?join_key=" + join_key + "&message_id=" + message_id;

    getMessageResponseId = llHTTPRequest(ait_endpoint + "/ait/getMessageResponse" + uriParams, [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "");
}

ait_startConversation(){
    string jsonBody = llList2Json(JSON_OBJECT, ["join_key", join_key]);

    startConversationId=llHTTPRequest(ait_endpoint + "/ait/startConversation", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
}

transmitMessage(string username, string message){
    
    pollingMessageId = llGenerateKey();
    pollingForResponse=1;
    polling_start_time = llGetUnixTime(); // Record when polling started
    llSetTimerEvent(1.0);

    // do not listen to public channel when polling
    llListenRemove(listener_public_channel);
    
    // Show polling indicator
    llSetText("waiting for response", <1.0, 1.0, 0.5>, 1.0);

    ait_postMessage(pollingMessageId, username, message);
}

validateModel(string modelToValidate)
{
    llOwnerSay("Validating model: " + modelToValidate);
    modelsValidationId = llHTTPRequest(ait_endpoint + "/chat_models", 
        [HTTP_METHOD, "GET", HTTP_MIMETYPE, "application/json"], "");
}

// Function to validate audio parameters against /voices endpoint
validateAudioParameters(string voiceToValidate, string audioModelToValidate)
{
    llOwnerSay("Validating audio voice: " + voiceToValidate + " and audio model: " + audioModelToValidate);
    voicesValidationId = llHTTPRequest(ait_endpoint + "/audio_models", 
        [HTTP_METHOD, "GET", HTTP_MIMETYPE, "application/json"], "");
}

// Function to check if a value exists in a JSON array
integer isValueInJsonArray(string jsonString, string value)
{
    // Simple check for the value in the JSON string
    // This is a basic implementation - in a real scenario you'd want more robust JSON parsing
    if (llSubStringIndex(jsonString, "\"" + value + "\"") != -1) {
        return TRUE;
    }
    return FALSE;
}

// Function to validate all parameters after they are loaded
validateAllParameters()
{
    if (join_key=="" || systemInstructions=="" || charactername=="") {
        // Cannot start validation, join_key, system instructions or charactername is missing
        return;
    }
    llOwnerSay("Starting parameter validation...");
    
    validateModel(model);
    
    validateAudioParameters(audio_voice, audio_model);

    llSetText("currently validating parameters", <1.0, 1.0, 0.5>, 1.0);
}

// Function to truncate command for dialog (max 24 characters)
string truncateDialogCommand(string commandPrefix, string name)
{
    string fullCommand = commandPrefix + name;
    if (llStringLength(fullCommand) <= 23) {
        return fullCommand;
    }
    return llGetSubString(fullCommand, 0, 22);
}


printInfo(){
    llOwnerSay("on channel " + command_channel + " to activate type the following: Activate " + charactername);
    llOwnerSay("on channel " + command_channel + " to activate only this character, type the following: spotlight " + charactername);
    llOwnerSay("on channel " + command_channel + " to activate all characters, type the following: ActivateAllCharacters");
}

// Function to show dialog interface
showDialog(key user)
{
    string status_text="Inactive";
    if (isActive==1){
        status_text = "Active";
    }
    string activateCmd = truncateDialogCommand("Activate ", charactername);
    string deactivateCmd = truncateDialogCommand("Deactivate ", charactername);
    string spotlightCmd = truncateDialogCommand("Spotlight ", charactername);
    llDialog(user, 
        "AIT Character: " + charactername + "\nJoin Key: " + join_key + "\nStatus: " + status_text + "\n\nWhat would you like to do?",
        [activateCmd, deactivateCmd, spotlightCmd, "Close"], 
        command_channel);
}

default
{
    state_entry()
    {
        // Verify the notecard exists
        if (llGetInventoryType(parametersNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + parametersNotecardName + "' not found. Please add it to the object.");
            return;
        }
        if (llGetInventoryType(systemNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + systemNotecardName + "' not found. Please add it to the object.");
            return;
        }
        if (llGetInventoryType(joinkeyNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + joinkeyNotecardName + "' not found. Please add it to the object.");
            return;
        }
        // Start reading the notecard from the first line

        optionsList = [];
        parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
        systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);

        joinkeyNotecardQueryId = llGetNotecardLine(joinkeyNotecardName, 0);

        // Clear any floating text on script start
        llSetText("", ZERO_VECTOR, 0.0);
    }

    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        
        if (fullyValidated) {
            showDialog(toucher);
        } else {
            llInstantMessage(toucher, "Configuration not validated. Please check that 'llm-parameters', 'llm-system' and 'join_key' notecards exist and contain valid data. Reset the script for more details.");
        }
    }

    dataserver(key query_id, string data)
    {
        if (query_id == parametersNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = data;

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
                    if (paramName == "audio_instructions") 
                    {
                        audio_instructions = value;
                    }
                    
                    // Check if this parameter is in any of our option lists
                    integer isStringListParam = (llListFindList(optionParameters_stringlist, [paramName]) != -1);
                    integer isIntParam = (llListFindList(optionParameters_integers, [paramName]) != -1);
                    integer isFloatParam = (llListFindList(optionParameters_floats, [paramName]) != -1);
                    
                    if (isStringListParam || isIntParam || isFloatParam) {
                        add_option(paramName, value);
                    }
                }
                // Get the next line
                parametersCurrentLine++;
                parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
            }
            else
            {

                if (charactername==""){
                    llOwnerSay("You need to add the parameter charactername in " + parametersNotecardName + " notecard!");
                    return;
                }
                
                // Now you have the entire notecard as a single string
                llOwnerSay("Parameter notecard content loaded:");
                llOwnerSay("charactername: " + charactername);
                llOwnerSay("model: " + model);
                llOwnerSay("audio_instructions: " + audio_instructions);
                llOwnerSay("audio_voice: " + audio_voice);
                llOwnerSay("audio_model: " + audio_model);
                
                validateAllParameters();
            }
        }
        if (query_id == systemNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = data;

                // Add this line to our collection
                systemNotecardLines += line;
                
                // Get the next line
                systemCurrentLine++;
                systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);
            }
            else
            {
                // We've reached the end of the notecard
                // Combine all lines into a single string with newlines
                systemInstructions = llDumpList2String(systemNotecardLines, "\\n");
                
                if (systemInstructions=="") {
                    llOwnerSay(systemNotecardName + " should not be empty for use as llm system instructions");
                    return;
                }
                // Now you have the entire notecard as a single string
                llOwnerSay("System instructions have been loaded:");
                llOwnerSay(systemInstructions);

                validateAllParameters();
            }
        }
        if (query_id == joinkeyNotecardQueryId)
        {
            if (data != EOF)
            {
                string line = data;

                join_key = line;

                if (join_key=="") {
                    llOwnerSay(joinkeyNotecardName + " has to contain a non-empty string for use as join_key");
                    return;
                }
                llOwnerSay("join_key has been read: " + join_key);
            } else {
                if (join_key=="") {
                    llOwnerSay(joinkeyNotecardName + " has to contain a non-empty string for use as join_key");
                    return;
                }
                validateAllParameters();
            }
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        if(channel == 0) {
            if (isActive==0){
                return;
            }
            // Don't process messages while waiting for HTTP response
            if (pollingForResponse == 1) {
                return;
            }
            if (llSubStringIndex(llToLower(message), llToLower(charactername)) == -1)
            {
                // charactername was not in the message
                return;
            }

            list parts = llParseString2List(name, ["@"], []);
            string username = llList2String(parts, 0);
            
            username = llStringTrim(username, 3);

            transmitMessage(username, message);
        }

        

        if (channel == command_channel) {
            if (id != llGetOwner()) {
                // uncomment here to allow anyone to trigger config commands
                llSay(0, "you are not allowed ...");
                llInstantMessage(id, "You are not allowed to use config commands.");
                return;
            }

            if (fullyValidated==0){
                llInstantMessage(id, "Parameters are not fully validated");
                return;
            }

            string ActivateAllCharactersCommand = "ActivateAllCharacters";
            if (message == ActivateAllCharactersCommand){
                llOwnerSay(charactername + " has been activated using ActivateAllCharacters command");
                listener_public_channel = llListen(0, "","","");
                llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);
                isActive = 1;
            }
            string DeactivateAllCharactersCommand = "DeactivateAllCharacters";
            if (message == DeactivateAllCharactersCommand){
                llOwnerSay(charactername + " has been deactivated using DeactivateAllCharacters command");
                llListenRemove(listener_public_channel);
                llSetText("currently inactive, click me for details", <1.0, 1.0, 0.5>, 1.0);
                isActive = 0;
            }
            string activateAgentCommand = "Activate " + charactername;
            string activateAgentCommandShort = truncateDialogCommand("Activate ", charactername);
            
            if (message == activateAgentCommand || message == activateAgentCommandShort){
                listener_public_channel = llListen(0, "","","");
                llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);
                llOwnerSay(charactername + " has been activated");
                isActive = 1;
            }
            string deactivateAgentCommand = "Deactivate " + charactername;
            string deactivateAgentCommandShort = truncateDialogCommand("Deactivate ", charactername);
            if (message == deactivateAgentCommand || message == deactivateAgentCommandShort){
                llOwnerSay(charactername + " has been deactivated");
                llListenRemove(listener_public_channel);
                llSetText("currently inactive, click me for details", <1.0, 1.0, 0.5>, 1.0);
                isActive = 0;
            }
            string spotlightActivateCommand = "Spotlight " + charactername;
            string spotlightActivateCommandShort = truncateDialogCommand("Spotlight ", charactername);
            if (message == spotlightActivateCommand || message == spotlightActivateCommandShort){
                llOwnerSay(charactername + " has been activated by spotlight command");
                listener_public_channel = llListen(0, "","","");
                llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);
                isActive = 1;
            } else {
                list commandParts = llParseString2List(message, [" "], []);
                string commandName = llList2String(commandParts, 0);

                if (commandName == "Spotlight") {
                    llOwnerSay(charactername + " has been deactivated by spotlight command");
                    llListenRemove(listener_public_channel);
                    llSetText("currently inactive, click me for details", <1.0, 1.0, 0.5>, 1.0);
                    isActive = 0;
                }
            }

            string directActivateCommand = "Direct " + charactername;
            if (llSubStringIndex(message, directActivateCommand) == 0) {
                string instruction = llGetSubString(message, llStringLength(directActivateCommand), -1);
                llOwnerSay(name + " has sent a director command to the server: "+ instruction);
                transmitMessage("Director", instruction);
            }
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == modelsValidationId) {
            if (status == 200) {
                string chatModels = llJsonGetValue(body, ["chat_models"]);
                string defaultModel = llJsonGetValue(body, ["default_model"]);

                if (model==""){
                    llOwnerSay("model was not specified in llm-parameters notecard, the AIT default model " + defaultModel + " will be used");
                    modelsValidated = 1;
                } else {
                    if (isValueInJsonArray(chatModels, model)) {
                        llOwnerSay("✓ Model '" + model + "' is valid");
                        modelsValidated = 1;
                    } else {
                        llOwnerSay("✗ Model '" + model + "' is NOT valid. Available models: " + chatModels);
                        modelsValidated = 0;
                    }
                }

                // Final validation summary
                if (modelsValidated && audioIsValidated) {
                    fullyValidated = 1;
                    llOwnerSay("✓ All parameters validated successfully!");
                    llSetText("currently inactive, click me for details", <1.0, 1.0, 0.5>, 1.0);
                    llListen(command_channel, "","","");
                    ait_startConversation();
                    printInfo();
                }
        
            } else {
                llOwnerSay("Error validating model: HTTP " + (string)status + " - " + body);
            }
            return;
        }
        
        if (request_id == voicesValidationId) {
            if (status == 200) {
                string audioAvailable = llJsonValueType(body, ["audio_available"]);
                
                if (audioAvailable==JSON_TRUE) {
                    string validVoices = llJsonGetValue(body, ["allowed_voices"]);
                    string audioModels = llJsonGetValue(body, ["audio_models"]);
                    string defaultVoice = llJsonGetValue(body, ["default_voice"]);
                    string defaultModel = llJsonGetValue(body, ["default_model"]);
                    
                    integer voiceValid=0;
                    if (audio_voice!=""){
                        voiceValid = isValueInJsonArray(validVoices, audio_voice);
                        if (voiceValid) {
                            llOwnerSay("✓ Audio voice '" + audio_voice + "' is valid");
                        } else {
                            llOwnerSay("✗ Audio voice '" + audio_voice + "' is NOT valid. Available voices: " + validVoices);
                        }
                    } else {
                        llOwnerSay("audio_voice was not specified in llm-parameters notecard, the AIT default voice " + defaultVoice + " will be used");
                        voiceValid = 1;
                    }
                    
                    integer audioModelValid = 0;
                    if (audio_model != ""){
                        audioModelValid = isValueInJsonArray(audioModels, audio_model);
                        if (audioModelValid) {
                            llOwnerSay("✓ Audio model '" + audio_model + "' is valid");
                        } else {
                            llOwnerSay("✗ Audio model '" + audio_model + "' is NOT valid. Available audio models: " + audioModels);
                        }
                    } else {
                        llOwnerSay("audio_model was not specified in llm-parameters notecard, the AIT default voice " + defaultVoice + " will be used");
                        audioModelValid = 1;
                    }
                    
                    if (voiceValid && audioModelValid) {
                        audioIsValidated=1;
                    } else {
                        audioIsValidated=0;
                    }
                    
                } else {
                    llOwnerSay("This AIT server is not configured for audio use");
                    audioIsValidated = 1;
                }
                
                
                // Final validation summary
                if (modelsValidated && audioIsValidated) {
                    fullyValidated = 1;
                    llOwnerSay("✓ All parameters validated successfully!");
                    llSetText("currently inactive, click me for details", <1.0, 1.0, 0.5>, 1.0);
                    llListen(command_channel, "","","");
                    ait_startConversation();
                    printInfo();
                }
                
            } else {
                llOwnerSay("Error validating audio parameters: HTTP " + (string)status + " - " + body);
            }
            return;
        }

        if (request_id == startConversationId) {
            string info = llJsonGetValue(body, ["info"]);
            llSay(0, info);
            return;
        }
        
        if (request_id == getMessageResponseId || request_id == postMessageId) {

            if(200 == status) {
                
                string message_id = llJsonGetValue(body, ["message_id"]);
                if (message_id!=(string) pollingMessageId){
                    return;
                }
                if (pollingForResponse==0){
                    // we already recieved the info
                    return;
                }

                // start listening to chat messages again
                pollingForResponse=0;
                listener_public_channel = llListen(0, "", "", "");
                
                // Show listening indicator
                llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);

                string response = llJsonGetValue(body, ["response"]);
                
                printResponse(response);

                return;
            } else if (status != 0 && status != 425 && status !=499) {
                // Stop polling on any error status (not 0, not 200, not 425, not 499)
                if (pollingForResponse == 1) {
                    pollingForResponse = 0;
                    listener_public_channel = llListen(0, "", "", "");
                    // Show listening indicator
                    llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);
                    llSay(0, "HTTP Error " + (string)status + ": " + body + " - Stopping polling");
                }
                return;
            }
        }
        
        if (425 == status) {
            // 425 means the response is not yet available from AI talkmaster
            return;
        } else if (0 == status) {
            // request Timeout in OpenSimulator: returns code 0 after 30 seconds
            return;
        } else if (499 == status) {
            // ignore 499 client timeouts, they occur frequently on OpenSimulator Community Conference grid
            return;
        } else if (200 == status) {
            // missed 200 (ID changed)
            return;
        } else {
            // Report all other status codes to owner
            llOwnerSay("HTTP Error " + (string)status + ": " + body);
            pollingForResponse = 0;
            listener_public_channel = llListen(0, "", "", "");
            
            // Show listening indicator
            llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);
        }
    }

    timer()
    {
        if (pollingForResponse == 1) {
            // Check if polling has timed out
            float current_time = llGetUnixTime();
            if (current_time - polling_start_time > polling_timeout) {
                llOwnerSay("Polling timeout reached (" + (string)polling_timeout + " seconds). Stopping polling for message: " + pollingMessageId);
                pollingForResponse = 0;
                // Resume listening to public channel
                listener_public_channel = llListen(0, "", "", "");
                
                // Show listening indicator
                llSetText("listening on channel 0", <1.0, 1.0, 0.5>, 1.0);
                return;
            }
            ait_getMessageResponse(pollingMessageId);
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

