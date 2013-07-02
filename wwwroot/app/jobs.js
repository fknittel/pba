function ActiveJobsController($scope, $http) {
    $scope.jobs = [];
 
    $scope.addJob = function() {
    	var new_job = {
        	sprinkler_id: $scope.sprinkler_id,
        	duration: parseInt($scope.duration),
    	    high_priority: false,
    	    };
	    $http({method: 'POST', url: '/jobs', data: new_job}).
		    success(function(data, status, headers, config) {
		    	$scope.refresh();
	  	    }).
		    error(function(data, status, headers, config) {
		    });
        $scope.sprinkler_id = '';
        $scope.duration = '';
    };
 
    $scope.refresh = function() {
	    $http({method: 'GET', url: '/jobs/active'}).
		    success(function(data, status, headers, config) {
		    	$scope.jobs = data;
	  	    }).
		    error(function(data, status, headers, config) {
		    	$scope.jobs = [];
		    });
    };
}
function WaitingJobsController($scope, $http) {
    $scope.jobs = [];
 
    $scope.refresh = function() {
	    $http({method: 'GET', url: '/jobs/waiting'}).
		    success(function(data, status, headers, config) {
		    	$scope.jobs = data;
	  	    }).
		    error(function(data, status, headers, config) {
		    	$scope.jobs = [];
		    });
    };
}
