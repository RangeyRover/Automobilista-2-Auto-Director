function latchJS(change) {
    // Setup the latch 
    if (root["latch"] == null) {
        root["latch"] = 0;
	}
	if (change == 1){
	if (root["latch"] == 0) { // Turn ON if already OFF
            root["latch"] = 1;
            return root["latch"];
       		}
       if (root["latch"] == 1) { // Turn OFF if already ON
        root["latch"] = 0;
        return root["latch"]; 		
		}
     
	}
    return root["latch"];
}



function findHighestOverallScoreJS(leader) {
  let highestScore = -Infinity; // Initialize with a very low value
  let driverPosition = null;
  let driverName = null;

  for (const driver of leader) {
    const overallScore = driver.overallScore;

    if (overallScore > highestScore) {
      highestScore = overallScore;
      driverPosition = driver.driverPosition;
      driverName = driver.driverName;
    }
  }

  return { highestScore, driverPosition, driverName };
}

function calculateSectorScoreJS(currentSectorTime, bestSectorTime, globalbestSectorTime) {
    if (currentSectorTime <= globalbestSectorTime) {
    return 10; // Award 10 points for each better global sector
  } else {
     if (currentSectorTime <= bestSectorTime) {
    return 5; // Award 5 points for each better sector
  } else {
    return 0; // No points awarded for sectors that are not better
  }
  }
 
}
function speedScoreJS(speed) {
  if (speed > 60) { //Award 15 points if car is moving above 60Kmh
    return 15;
  } else {
    return 0;
  }
}
function calculatePitScoreJS(pitStatus) {
  if (pitStatus != '0') { //Award 15 points if car is on the track
    return -30;
  } else {
    return 0;
  }
}
function updateLapValidScoreJS(driver, lapValidScore, lapValid) { //Take-15Points off if lap is invalid
  if (lapValid != 1) {
    return lapValidScore = - 15;
  } else {
    return lapValidScore = 0;
  }
}
function countParticipantsJS() { //find how many drivers
	if (root["timer"] == null) {
  root["NumberDrivers"] = 0;
  root["timer"] = 59;
}
root["timer"] = root["timer"] + 1;
	if (root["timer"] == 60) {
    root["timer"] = 0;
	  const numberDrivers = [];

  // Iterate from 1 to 60 to find how many drivers
  for (let i = 1; i <= 60; i++) {
    const propValue = $prop(`GarySwallowDataPlugin.Leaderboard.Position${i < 10 ? '0' : ''}${i}.DriverStatus`);

    if (propValue === "On Track" || propValue === "In Garage" || propValue === "In Pits") {
      // Send to Array if in race
      numberDrivers.push(propValue);
    }
  }
  root["NumberDrivers"] = numberDrivers.length;
  return numberDrivers.length;
	}
else {
return root["NumberDrivers"];	
}
}
