pragma solidity >=0.4.0 <0.6.0;


contract BenchContract {


    mapping(string => string) public map;

    function writeData(string memory _key, string memory _value) public {
        map[_key] = _value;
    }

    function readData(string memory _key) public view returns(string memory) {
        return map[_key];
    }

    function doNothing() public {
    }

    function matMultHelper(uint[][] memory mat1, uint[][] memory mat2) private pure returns (uint) {
        uint r1 = mat1.length; // rows of mat1
        uint c1 = mat1[0].length; // columns of mat1
        uint c2 = mat2[0].length; // columns of mat1
        uint sum;
        uint matrixSum;

        uint[][] memory result = new uint[][](c1);

        for (uint i=0; i < c1; i++) {
            uint[] memory temp = new uint[](c1);
            for(uint j = 0; j < c1; j++){
                temp[j]=i+j;
            }
            result[i] = temp;
        }

        for(uint i = 0; i < r1; ++i) {
            for(uint j = 0; j < c2; ++j) {
                sum = 0;
                for(uint k = 0; k < c1; ++k) {
                sum += mat1[i][k] * mat2[k][j];
                }
                result[i][j] = sum;
            }
        }

        for(uint i = 0; i < result.length; ++i) {
            for (uint j = 0; j < result[i].length; ++j){
                matrixSum += result[i][j];
            }
        }
        return(matrixSum);
    }

     function matrixMultiplication(uint n) public pure returns (uint){
        uint f = 1;
        uint[][] memory mat1 = new uint[][](n);

        for (uint i=0; i < n; i++) {
            uint[] memory temp = new uint[](n);
            for(uint j = 0; j < n; j++){
                temp[j]=i+j;
            }
            mat1[i] = temp;
        }

        uint[][] memory mat2 = mat1;

        for (uint i=0; i<n; i++){
            for (uint j=0; j<n; j++){
            mat1[i][j] = f;
            f = f+1;
            }
        }
        mat2 = mat1;
        return matMultHelper(mat1, mat2);
    }
}