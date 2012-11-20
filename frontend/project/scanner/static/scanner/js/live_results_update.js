var num_high_risk = 0;
var num_medium_risk = 0;
var num_low_risk = 0;
var num_info_risk = 0;
var since_token = ""
var looping_interval = setInterval(queryUpdate, 2000);

//Function to dynamically create a table to append to the "High" "Med" or "Low" risks detailed results area
function createResultTable(issue) {
    var table_to_add = $('<table></table').addClass('table table-bordered table-results');
    var thead_to_add = $('<thead></thead>').addClass('results_table_expander').append('<tr><th><span class=\"plus_minus\">+</span> ' + issue['Summary'] + '</th></tr></thead>');
    thead_to_add.click(function()
    {
        $(this).next(".results_table_area").toggle();
        if($(this).find($('.plus_minus')).text() == "+") {
            $(this).find($('.plus_minus')).text("-");
        } else {
            $(this).find($('.plus_minus')).text("+");
        }
    });
    table_to_add.append(thead_to_add);
    var tbody_to_add = $('<tbody></tbody>').addClass('results_table_area');
    $.each(issue, function(key, value) {
        tbody_to_add.append('<tr><td>' + key + '</td><td>' + value + '</td></tr>');
    });
    tbody_to_add.hide();
    table_to_add.append(tbody_to_add);
    return table_to_add;
}

//Runs every x interval to retrieve results from API and update interface appropriately
function queryUpdate() {
    $.post("/en-US/xhr_scan_status/", {
        "scan_id":scan_id,
        "token":since_token
    },
    function(data) {
        var json_data = jQuery.parseJSON(data);
        var added_overall_progress = 0;
        var num_plugins = 0;    //Use this to divide and get average progress
        
        $.each(json_data.scan.sessions, function(i, result) {
            
            //Loop through each of the issues associated with the current plugin
            $.each(result.issues, function(i, issue) {
                //$("#updating_results").val($("#updating_results").val() + "From Plugin: " + result['plugin_name'] + "\nSeverity: " + issue['Severity'] + "\nSummary: " + issue['Summary'] + "\n\n");
                if(issue['Severity'] === "High") {
                    num_high_risk += 1;
                } else if(issue['Severity'] === "Medium") {
                    num_medium_risk += 1;
                } else if (issue['Severity'] === "Low") {
                    num_low_risk += 1;
                } else if(issue['Severity'] === "Informational" || issue['Severity'] === "Info") {
                    num_info_risk += 1;
                }
                var tr_to_add = $("<tr></tr>")
                var severity = 
                tr_to_add.append("<td><div class=\"severity alert-" + issue['Severity'].toLowerCase() + "\">" + issue['Severity'] + "</div></td><td>" + result['plugin']['name'] + "</td>");
                var td_to_add = $("<td></td>");
                td_to_add.append(createResultTable(issue));
                tr_to_add.append(td_to_add);
                $("#results_table_tbody").append(tr_to_add);
            });
            
            //Update progress bars
            var div_id = result['id'];
            //Try catch in case null is returned for progress in plugins that don't support percentage
            try {
                var progress = parseInt(result['progress']) || 0;
            } catch (err) {
                var progress = 0;
            }
            
            if(result['state'] === "FAILED") {
                $("#"+div_id+"_prog").removeClass("progress-info").addClass("progress-danger");
                progress = 100;
            } else if(result['state'] === "FINISHED") {
                progress = 100;
            }
            
            added_overall_progress += progress;
            num_plugins += 1;
            
            $("#" + div_id).css("width", progress.toString() + "%");
        });
        
        var avg_overall_progress = added_overall_progress / num_plugins;
        $("#overall_progress").css("width", avg_overall_progress.toString() + "%");
        
        //Update risk counters
        $("#num_high_risk").text(num_high_risk.toString());
        $("#num_medium_risk").text(num_medium_risk.toString());
        $("#num_low_risk").text(num_low_risk.toString());
        $("#num_info_risk").text(num_info_risk.toString());
        
        since_token = json_data["token"];
        if(since_token === null) {
            clearInterval(looping_interval);
            $("#scanning_gif").hide();
            $("#scan_status_label").text("Scan is finished running.");
        }
    });
}
