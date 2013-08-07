function JobsController($scope, $http) {
    $scope.duration = '120';
    $scope.addJob = function(sprinkler_id) {
        var new_job = {
            sprinkler_id: sprinkler_id,
            duration: parseInt($scope.duration),
            high_priority: false,
            };
        $http({method: 'POST', url: '/jobs', data: new_job}).
            success(function(data, status, headers, config) {
                $scope.refresh();
            }).
            error(function(data, status, headers, config) {
            });
    };
}

function ActiveJobsController($scope, $http) {
    $scope.jobs = [];
 
    $scope.removeJob = function(sprinkler_id) {
        $http({method: 'DELETE', url: '/jobs/active/' + sprinkler_id}).
            success(function(data, status, headers, config) {
                $scope.refresh();
            }).
            error(function(data, status, headers, config) {
            });
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

    $scope.refresh();
}

function WaitingJobsController($scope, $http) {
    $scope.jobs = [];
  
    $scope.removeJob = function(sprinkler_id) {
        $http({method: 'DELETE', url: '/jobs/waiting/' + sprinkler_id}).
            success(function(data, status, headers, config) {
                $scope.refresh();
            }).
            error(function(data, status, headers, config) {
            });
    };

    $scope.refresh = function() {
        $http({method: 'GET', url: '/jobs/waiting'}).
            success(function(data, status, headers, config) {
                $scope.jobs = data;
            }).
            error(function(data, status, headers, config) {
                $scope.jobs = [];
            });
    };
    
    $scope.refresh();
}
