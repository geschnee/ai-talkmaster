// script by Herzstein Dev
// This script provides a way of interacting with the AI Talkmaster Translation functionality.
// The translation functionality translates text from one language to another and generates audio.
// When the user clicks the object, it sends the user's next message to the AI Talkmaster server and prints the translated response.
// More details at https://github.com/geschnee/ai-talkmaster

string ait_endpoint = "https://hg.hypergrid.net:6000";


integer listener;
string input_message;
key user=NULL_KEY;
string username ="";
key message_id=NULL_KEY;
float reserveTime = 600.0;
float pollFreq = 2.0;
float stopwatch;


// Validation variables
key modelsValidationId;
integer modelsValidated = 0;
integer validationInProgress = 0;

// HTTP request tracking
key postMessageId;
key getMessageResponseId;

// Notecard completion tracking
integer notecardsCompleted = 0;
integer PARAMETERS_NOTECARD_COMPLETED = 1;
integer ALL_NOTECARDS_COMPLETED = 1;

integer max_response_length = 16384;

integer MAX_LENGTH = 1024;    // Maximum string length in LSL

// Polling timeout variables
float polling_start_time = 0.0;
float polling_timeout = 300.0; // Stop polling after 5 minutes


// Read Entire Notecard as Single String
string parametersNotecardName = "translation-parameters";
key parametersNotecardQueryId;
integer parametersCurrentLine= 0;


string session_key;
string model;
string source_language;
string target_language;
string audio_voice;
string audio_model;
string audio_instructions;

// Translation parameters - no options list needed


// Function to unescape JSON string values (converts \" to " and other escape sequences)
string unescapeJsonString(string jsonStr) {
    // Replace escaped quotes with actual quotes
    jsonStr = llReplaceSubString(jsonStr, "\\\"", "\"", 0);
    // Replace other common JSON escape sequences
    jsonStr = llReplaceSubString(jsonStr, "\\n", "\n", 0);
    jsonStr = llReplaceSubString(jsonStr, "\\t", "\t", 0);
    jsonStr = llReplaceSubString(jsonStr, "\\r", "\r", 0);
    jsonStr = llReplaceSubString(jsonStr, "\\\\", "\\", 0);
    return jsonStr;
}

// Function to print response text, splitting into chunks if necessary
printResponse(string response) {
    // Unescape JSON escape sequences to get proper quotation marks
    response = unescapeJsonString(response);
    
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
        llSay(0, (string) j_plus + " " + (string) chunk);
    }
}

// Translation doesn't use options, removed option handling functions

translation_translate(string input_message) {
    // Check if model validation has completed and failed
    if (validationInProgress == 0 && modelsValidated == 0) {
        llSay(0, "Model '" + model + "' is not available on the server. Please check your configuration.");
        return;
    }
    
    // If validation is still in progress, wait
    if (validationInProgress == 1) {
        llSay(0, "Model validation is still in progress. Please wait...");
        return;
    }

    // Validate required parameters
    if (session_key == "") {
        llSay(0, "Error: session_key is required. Please set it in the translation-parameters notecard.");
        return;
    }
    if (source_language == "") {
        llSay(0, "Error: source_language is required. Please set it in the translation-parameters notecard.");
        return;
    }
    if (target_language == "") {
        llSay(0, "Error: target_language is required. Please set it in the translation-parameters notecard.");
        return;
    }

    // Generate a unique message_id for this request
    message_id = llGenerateKey();
    
    // Build JSON body with required and optional fields
    list jsonFields = ["session_key", session_key, "message", input_message, "source_language", source_language, "target_language", target_language, "message_id", (string)message_id];
    
    if (model != "") {
        jsonFields += ["model", model];
    }
    if (audio_voice != "") {
        jsonFields += ["audio_voice", audio_voice];
    }
    if (audio_model != "") {
        jsonFields += ["audio_model", audio_model];
    }
    if (audio_instructions != "") {
        jsonFields += ["audio_instructions", audio_instructions];
    }
    
    string jsonBody = llList2Json(JSON_OBJECT, jsonFields);

    postMessageId = llHTTPRequest(ait_endpoint + "/translation/translate", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
}

translation_getTranslation(string input_message) {
    // Check if model validation has completed and failed
    if (validationInProgress == 0 && modelsValidated == 0) {
        llSay(0, "Model '" + model + "' is not available on the server. Please check your configuration.");
        return;
    }
    
    // If validation is still in progress, wait
    if (validationInProgress == 1) {
        llSay(0, "Model validation is still in progress. Please wait...");
        return;
    }

    // Validate session_key is set
    if (session_key == "") {
        llSay(0, "Error: session_key is required. Please set it in the translation-parameters notecard.");
        return;
    }

    string uriParams = "?session_key=" + llEscapeURL(session_key) + "&message_id=" + llEscapeURL((string)message_id);
    
    getMessageResponseId = llHTTPRequest(ait_endpoint + "/translation/getTranslation" + uriParams, [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "");
}

set_ready() {
    llListenRemove(listener);
    llSetTimerEvent(0);
    user=NULL_KEY;
    input_message="";
    message_id=NULL_KEY;
    // Clear polling indicator
    llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
    llSay(0, "Please click on me to start a new session.");
    llSay(0, "---");
}


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
    // Check required parameters before starting validation
    if (session_key == "") {
        llOwnerSay("Error: session_key is empty. Please set it in the translation-parameters notecard. Validation skipped.");
        return;
    }
    if (source_language == "") {
        llOwnerSay("Error: source_language is empty. Please set it in the translation-parameters notecard. Validation skipped.");
        return;
    }
    if (target_language == "") {
        llOwnerSay("Error: target_language is empty. Please set it in the translation-parameters notecard. Validation skipped.");
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
            llOwnerSay("Error: Notecard '" + parametersNotecardName + "' not found. Please add it to the object.");
            return;
        }
        // Start reading the notecard from the first line
        parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);

        set_ready();
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
                    string value = llStringTrim(llList2String(splits, 1), STRING_TRIM);

                    if (paramName == "session_key") 
                    {
                        session_key = value;
                    }
                    if (paramName == "model") 
                    {
                        model = value;
                    }
                    if (paramName == "source_language") 
                    {
                        source_language = value;
                    }
                    if (paramName == "target_language") 
                    {
                        target_language = value;
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
                }
                // Get the next line
                parametersCurrentLine++;
                parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
            }
            else
            {
                // Now you have the entire notecard loaded
                llOwnerSay("Parameter notecard content loaded:");
                llOwnerSay("session_key: " + session_key);
                llOwnerSay("model: " + model);
                llOwnerSay("source_language: " + source_language);
                llOwnerSay("target_language: " + target_language);
                if (audio_voice != "") {
                    llOwnerSay("audio_voice: " + audio_voice);
                }
                if (audio_model != "") {
                    llOwnerSay("audio_model: " + audio_model);
                }
                if (audio_instructions != "") {
                    llOwnerSay("audio_instructions: " + audio_instructions);
                }
              
                notecardsCompleted = notecardsCompleted | PARAMETERS_NOTECARD_COMPLETED;
                
                // Check if all notecards are completed
                if (notecardsCompleted == ALL_NOTECARDS_COMPLETED) {
                    validateAllParameters();
                }
            }
        }
    }

    touch_start(integer num_detected)
    {
        if (notecardsCompleted != ALL_NOTECARDS_COMPLETED) {
            llSay(0, "Error reading config. Please check that 'translation-parameters' notecard exists and contains valid data. Reset the script for more details.");
            return;
        }
        if (user!=NULL_KEY & llDetectedKey(0) != user) {
            llSay(0, "Sorry I am currently in use by " + llKey2Name(user) + ". Please await your turn." );
        } else {
            user = llDetectedKey(0);
            
            llSay(0, "Hello "+llKey2Name(user)+" I am a translation service. I will translate your text from " + source_language + " to " + target_language + ". I can deal only with one user at a time."); 
            username = llKey2Name(user);
            llSetText("Please enter text in " + source_language + " to translate to " + target_language + ".", <1.0, 1.0, 0.5>, 1.0);
            listener = llListen(0, "", user, "");
            stopwatch = 0;
            input_message="";
            llSetTimerEvent(pollFreq);
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        if(channel == 0 && id == user) {
            stopwatch=0;
            input_message = message;
            polling_start_time = llGetUnixTime(); // Record when polling started
            // Show polling indicator
            llSetText("waiting for translation", <1.0, 1.0, 0.5>, 1.0);
            translation_translate(message);
            llListenRemove(listener);
        }   
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == modelsValidationId) {
            if (status == 200) {
                llOwnerSay("Models validation response received");
                string chatModels = llJsonGetValue(body, ["chat_models"]);
                string defaultModel = llJsonGetValue(body, ["default_model"]);

                if (model==""){
                    llOwnerSay("model was not specified in translation-parameters notecard, the AIT default model " + defaultModel + " will be used");
                    modelsValidated = 1;
                } else {
                    if (isValueInJsonArray(chatModels, model)) {
                        llOwnerSay("✓ Model '" + model + "' is valid");
                        modelsValidated = 1;
                        llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
                    } else {
                        llOwnerSay("✗ Model '" + model + "' is NOT valid. Available models: " + chatModels);
                        modelsValidated = 0;
                    }
                }
                
                validationInProgress = 0;
            } else {
                llOwnerSay("Error validating model: HTTP " + (string)status + " - " + body);
                validationInProgress = 0;
            }
            return;
        }
        
        // Handle translation/translate and translation/getTranslation responses
        if (request_id == postMessageId || request_id == getMessageResponseId) {
            if(200 == status) {
                // This is a successful translation response from getTranslation
                string message_id_rtn = llJsonGetValue(body, ["message_id"]);
                if (message_id_rtn != (string)message_id) {
                    return;
                }

                string translated_text = llJsonGetValue(body, ["translated_text"]);
                string original_message = llJsonGetValue(body, ["original_message"]);
                string source_lang = llJsonGetValue(body, ["source_language"]);
                string target_lang = llJsonGetValue(body, ["target_language"]);

                llSay(0, username+" translation result: ");
                llSay(0, "Original (" + source_lang + "): " + original_message);
                llSay(0, "Translated (" + target_lang + "): ");

                printResponse(translated_text);

                llSay(0, "Thank you for using the translation service "+username+".");
                
                set_ready();
                
                return;
            } else if (status != 0 && status != 425 && status != 499) {
                // Stop polling on any error status (not 0, not 200, not 425, not 499)
                if (input_message != "") {
                    // Clear polling indicator
                    llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
                    llSay(0, "HTTP Error " + (string)status + ": " + body + " - Stopping polling");
                    set_ready();
                } else {
                    // Report error but we're not polling
                    llOwnerSay("HTTP Error " + (string)status + ": " + body);
                }
                return;
            }
        }
        
        if (425 == status) {
            // 425 means the translation is still being processed
            // Check if this is the initial POST response with stream_url
            if (request_id == postMessageId) {
                string stream_url = llJsonGetValue(body, ["stream_url"]);
                if (stream_url != "") {
                    llSay(0, "Translation request queued. Audio stream available at: " + stream_url);
                }
            }
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
        }
    }

    timer()
    {
        // Invoked after every pollFreq seconds.
        stopwatch=stopwatch+pollFreq;    
        float remaining = reserveTime - stopwatch;
        // If the remaining seconds have exhausted.
        if(remaining<=0.0) {
            llSay(0, "Sorry timed out. I shall restart now.");
            set_ready();
        } else {
            if (input_message != "") {
                // Check if polling has timed out
                float current_time = llGetUnixTime();
                if (current_time - polling_start_time > polling_timeout) {
                    llOwnerSay("Polling timeout reached (" + (string)polling_timeout + " seconds). Stopping polling for message: " + input_message);
                    
                    // Clear polling indicator
                    llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
                    
                    llSay(0, "Sorry, the translation took too long. Please try again.");
                    set_ready();
                    return;
                }
                translation_getTranslation(input_message);
            }
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