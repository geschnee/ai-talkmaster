// This script is used to define a character for AI Talkmaster conversations.
// The script can be in state active and inactive.
// When active it listens to messages that mention the character's name.
// When it's name is mentioned by a whitelisted user or character, it sends a request to the AI Talkmaster and waits for the generated response, which is then said by the character.
// More details at https://github.com/geschnee/ai-talkmaster

integer config_channel = 8;

integer com_channel = 0;
integer listener_public_channel;
string prompt;
key user=NULL_KEY;
string username ="";
float reserveTime = 180.0;
float pollFreq = 2.0;
float stopwatch;

string ait_endpoint = "http://hg.hypergrid.net:6000";


float conversation_time=0;
integer conversation_message_id= 0;
integer pollingResponse=0;
float polling_start_time = 0.0;
float polling_timeout = 60.0; // Stop polling after 30 seconds

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


string charactername;
string model;
string systemInstructions;
string audio_description;
string audio_voice;
string audio_model;

string optionstring;
list optionStringParts=[];

list optionParameters = [
    "num_ctx", "repeat_last_n","repeat_penalty","temperature","seed","stop","num_predict","top_k","top_p","min_p"
];


list whitelisted_users = [];
string whitelistNotecardName = "whitelist";
key whitelistNotecardQueryId;
integer whitelistCurrentLine=0;

string joinkeyNotecardName = "join_key";
key joinkeyNotecardQueryId;
string join_key;

// Validation variables
key modelsValidationId;
key voicesValidationId;
integer modelsValidated = 0;
integer voicesValidated = 0;
integer validationInProgress = 0;

integer queue_code= 0;

integer isActive = 0;

string pollingMessageId;
string waitingForApprovalMessage;
string waitingForApprovalUsername;

// Function to split text into chunks
list splitText(string text)
{
    list chunks = [];
    integer textLength = llStringLength(text);
    
    // If text is already short enough, return it as a single chunk
    if (textLength <= MAX_LENGTH)
    {
        return [text];
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


post_message(string message_id, string username, string message) {

    string body = "{
        \"join_key\": \""+join_key+"\",
        \"username\": \""+username+"\",
        \"message\": \""+message+"\",
        \"model\": \""+model+"\",
        \"system_instructions\": \"" + systemInstructions +"\",
        \"charactername\": \""+charactername+"\",
        \"message_id\": \""+message_id+ "\",
        \"options\": " + optionstring +",
        \"audio_description\": \"" + audio_description + "\",
        \"audio_voice\": \""+ audio_voice + "\",
        \"audio_model\": \"" + audio_model + "\" 
    }";
    llHTTPRequest(ait_endpoint + "/ait/postMessage", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], body);
}

call_response(string message_id) {
    llHTTPRequest(ait_endpoint + "/ait/getMessageResponse", [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"join_key\": \""+join_key+"\",
        \"message_id\": \""+message_id+"\"
    }");
}

transmitMessage(string username, string message){
    queue_code += 1;
    string message_id = charactername + queue_code;

    pollingMessageId = message_id;
    pollingResponse=1;
    polling_start_time = llGetUnixTime(); // Record when polling started

    // do not listen to public channel when polling
    llListenRemove(listener_public_channel);

    

    post_message(message_id, username, ReplaceQuotesForJson(message));
}

string ReplaceQuotesForJson(string input)
{
    // Split on "
    list parts = llParseString2List(input, ["\""], []);
    // Join back with replacement
    return llDumpList2String(parts, "\\\"");
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
    modelsValidationId = llHTTPRequest(ait_endpoint + "/chat_models", 
        [HTTP_METHOD, "GET", HTTP_MIMETYPE, "application/json"], "");
}

// Function to validate audio parameters against /voices endpoint
validateAudioParameters(string voiceToValidate, string audioModelToValidate)
{
    validationInProgress = 1;
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
    if (model == "" || audio_voice == "" || audio_model == "") {
        llOwnerSay("Error: Some parameters are missing. Cannot validate.");
        return;
    }
    
    llOwnerSay("Starting parameter validation...");
    validateModel(model);
}

default
{
    state_entry()
    {
        // Verify the notecard exists
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
        if (llGetInventoryType(whitelistNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + whitelistNotecardQueryId + "' not found.");
            return;
        }
        // Start reading the notecard from the first line

        start_optionstring();
        parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
        systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);

        joinkeyNotecardQueryId = llGetNotecardLine(joinkeyNotecardName, 0);

        key ownerKey = llGetOwner();         
        string ownerName = llKey2Name(ownerKey);
        whitelisted_users += [ownerName];
        whitelistNotecardQueryId = llGetNotecardLine(whitelistNotecardName, whitelistCurrentLine);


        llListen(config_channel, "","","");

        queue_code = 0;
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
                
                // Now you have the entire notecard as a single string
                llOwnerSay("Parameter notecard content loaded:");
                llOwnerSay("charactername: " + charactername);
                llOwnerSay("model: " + model);
                llOwnerSay("audio_description: " + audio_description);
                llOwnerSay("audio_voice: " + audio_voice);
                llOwnerSay("audio_model: " + audio_model);
                
                finish_optionstring();
                llOwnerSay("optionstring: " + optionstring);

                
                validateAllParameters();

                llOwnerSay("on channel " + config_channel + " to activate type the following: activate " + charactername);
                llOwnerSay("on channel " + config_channel + " to activate only this actor, type the following: spotlight " + charactername);
                llOwnerSay("on channel " + config_channel + " to activate all actors, type the following: ActivateAllCharacters");
            }
        }
        if (query_id == systemNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = [data];

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
                string entireContent = llDumpList2String(systemNotecardLines, "\\n");
                
                // Now you have the entire notecard as a single string
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
                llSetTimerEvent(1.0);
            }
        }

        if (query_id == whitelistNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = [data];
                whitelisted_users += [line];
                
                // Get the next line
                whitelistCurrentLine++;
                whitelistNotecardQueryId = llGetNotecardLine(whitelistNotecardName, whitelistCurrentLine);
            }
            else
            {
                
                // Now you have the entire notecard as a single string
                llOwnerSay("Whitelist loaded:");
                integer i = 0;
                for (i = 0; i < llGetListLength(whitelisted_users); ++i)
                {
                    // Convert each element to string for printing
                    llOwnerSay(llList2String(whitelisted_users, i));
                }

            }
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        if (id == llGetKey())
        {
            return;
        }


        if(channel == 0) {
            if (isActive==0){
                return;
            }
            if (llSubStringIndex(llToLower(message), llToLower(charactername)) == -1)
            {
                // charactername was not in the message
                return;
            }

            string username = llParseString2List(name, ["@"], [])[0];
            username = llStringTrim(username, 3);

            waitingForApprovalUsername = username;

            if (llListFindList(whitelisted_users, [username]) == -1){

                queue_code += 1;
                waitingForApprovalMessage = message;
                
                llOwnerSay(name + " sent message: " + message + " but is not in list of approved speakers, to approve the message, type command on channel " + config_channel + ": approve " + charactername + " " + queue_code );

                return;
            } else {
                transmitMessage(username, message);
            }
            
        }
        if (channel == config_channel) {
            string username = llParseString2List(name, ["@"], [])[0];
            username = llStringTrim(username, 3);
            if (llListFindList(whitelisted_users, [username]) == -1){
                llOwnerSay(name + " is not in list of approved speakers");
                return;
            }
            string approveMessageCommand = "approve " + charactername + " " + queue_code;
            if (message == approveMessageCommand){
                transmitMessage(waitingForApprovalUsername, waitingForApprovalMessage);
            }

            string ActivateAllCharactersCommand = "ActivateAllCharacters";
            if (message == ActivateAllCharactersCommand){
                llOwnerSay(charactername + " has been activated using ActivateAllCharacters command");
                listener_public_channel = llListen(0, "","","");
                isActive = 1;
            }
            string DeactivateAllCharactersCommand = "DeactivateAllCharacters";
            if (message == DeactivateAllCharactersCommand){
                llOwnerSay(charactername + " has been deactivated using DeactivateAllCharacters command");
                isActive = 0;
            }
            string activateAgentCommand = "activate " + charactername;
            if (message == activateAgentCommand){
                listener_public_channel = llListen(0, "","","");
                llOwnerSay(charactername + " has been activated");
                isActive = 1;
            }
            string deactivateAgentCommand = "deactivate " + charactername;
            if (message == deactivateAgentCommand){
                llOwnerSay(charactername + " has been deactivated");
                isActive = 0;
            }
            string spotlightActivateCommand = "spotlight " + charactername;
            if (message == spotlightActivateCommand){
                llOwnerSay(charactername + " has been activated by spotlight command");
                listener_public_channel = llListen(0, "","","");
                isActive = 1;
            } else {
                string commandName = llParseString2List(message, [" "], [])[0];
                if (commandName == "spotlight") {
                    llOwnerSay(charactername + " has been deactivated by spotlight command");
                    isActive = 0;
                }
            }

            if (llGetListLength(llParseString2List(message, [" "], [])) >= 2) {
                string command = llParseString2List(message, [" "], [])[0] + " " + llParseString2List(message, [" "], [])[1];
                if (command == "direct "+ charactername) {
                    string instruction = llGetSubString(message, llStringLength(command), -1);
                    llOwnerSay(name + " has sent a director command to the server: "+ instruction);
                    transmitMessage("Director", instruction);
                }
            }
            
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == modelsValidationId) {
            if (status == 200) {
                llOwnerSay("Models validation response received");
                string chatModels = llJsonGetValue(body, ["chat_models"]);
                if (isValueInJsonArray(chatModels, model)) {
                    llOwnerSay("✓ Model '" + model + "' is valid");
                    modelsValidated = 1;
                } else {
                    llOwnerSay("✗ Model '" + model + "' is NOT valid. Available models: " + chatModels);
                    modelsValidated = 0;
                }
                
                // After model validation, validate audio parameters
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
                
                // Final validation summary
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
        
        // Handle regular AI response
        if(200 == status) {
            
            string message_id = llJsonGetValue(body, ["message_id"]);
            if (message_id!=(string) pollingMessageId){
                return;
            }
            if (pollingResponse==0){
                // we already recieved the info
                return;
            }

            // start listening to chat messages again
            pollingResponse=0;
            listener_public_channel = llListen(0, "", "", "");

            string response = llJsonGetValue(body, ["response"]);
            
            string trimmed_response = deleteUpToSubstring(response, "</think>");
            trimmed_response = llStringTrim(trimmed_response, STRING_TRIM);

            list chunks = splitText(trimmed_response);
            integer i;
            for (i = 0; i < llGetListLength(chunks); ++i)
            {
                string chunk = llList2String(chunks, i);
                integer i_plus = i + 1;
                llSay(0, i_plus + " " + chunk);
            }
            
        } else if (425 == status) {
            // 425 means the response is not yet available from AI talkmaster
            return;
        } else if (0 == status) {
            // Timeout/no reply
            return;
        } else {
            // Report all other status codes to owner
            llOwnerSay("HTTP Error " + (string)status + ": " + body);
        }
    }

    timer()
    {
        if (pollingResponse == 1) {
            // Check if polling has timed out
            float current_time = llGetUnixTime();
            if (current_time - polling_start_time > polling_timeout) {
                llOwnerSay("Polling timeout reached (" + (string)polling_timeout + " seconds). Stopping polling for message: " + pollingMessageId);
                pollingResponse = 0;
                // Resume listening to public channel
                listener_public_channel = llListen(0, "", "", "");
                return;
            }
            call_response(pollingMessageId);
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