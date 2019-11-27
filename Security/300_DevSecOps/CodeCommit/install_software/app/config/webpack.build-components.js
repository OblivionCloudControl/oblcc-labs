const path = require('path');
const webpack = require('webpack');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const UglifyJSPlugin = require('uglifyjs-webpack-plugin');

module.exports = {
  entry : {
    app : './src/components/index.js'
  },
  devtool : 'source-map',
  plugins : [
    new CleanWebpackPlugin(['dist']),
    new HtmlWebpackPlugin({
      title : 'Production'
    }),
    // new UglifyJSPlugin({
    //   sourceMap : true
    // }),
    new webpack.DefinePlugin({
      'process.env.NODE_ENV' : JSON.stringify('production')
    })
  ],
  output : {
    path : path.resolve(__dirname, '../dist'),
    filename : 'index.js',
    library: 'internal-fe-components',
    libraryTarget: 'umd',
    publicPath: '/dist/',
    umdNamedDefine: true
  },
  resolve : {
    extensions : ['.js', '.jsx', '.css', '.scss']
  },
  externals: {
    // Don't bundle react or react-dom
    react: {
      commonjs: "react",
      commonjs2: "react",
      amd: "React",
      root: "React"
    },
    "react-dom": {
      commonjs: "react-dom",
      commonjs2: "react-dom",
      amd: "ReactDOM",
      root: "ReactDOM"
    }
  },
  module : {
    rules : [
      // =========
      // = Babel =
      // =========
      // Load jsx extensions with babel so we can use
      // 'import' instead of 'require' and es6 syntaxwe
      {
        test : /\.jsx?$/,
        include : path.resolve(__dirname, '../src'),
        loader : "babel-loader",
        options : {
          // This is a feature of `babel-loader` for Webpack (not Babel itself).
          // It enables caching results in ./node_modules/.cache/babel-loader/
          // directory for faster rebuilds.
          cacheDirectory : true,

          // Disable loading default .babelrc and just use babelrc config in this file
          babelrc : false,

          "presets" : [
            "env",
            "react"
          ],
          "plugins" : [
            "transform-runtime",
            "transform-decorators-legacy",
            "transform-class-properties",
            "transform-object-rest-spread",
            "transform-es2015-modules-umd"
          ],
          "env" : {
            "targets" : {
              // The % refers to the global coverage of users from browserslist
              "browsers" : [
                ">0.25%",
                "not op_mini all"
              ]
            }
          }
        }
      },
      // =========
      // = Fonts =
      // =========
      {
        test : /\.eot(\?v=\d+\.\d+\.\d+)?$/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : ["file-loader"]
      },
      {
        test : /\.(woff|woff2)$/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : [
          {
            loader : "url-loader",
            options : {prefix : "font", limit : 5000}
          }
        ]
      },
      {
        test : /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : [
          {
            loader : "url-loader",
            options : {
              prefix : "font",
              limit : 10000,
              mimetype : "application/octet-stream"
            }
          }
        ]
      },
      // ==========
      // = Images =
      // ==========
      {
        test : /\.svg(\?v=\d+\.\d+\.\d+)?$/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : [
          {
            loader : "url-loader",
            options : {
              limit : 50000,
              mimetype : "image/svg+xml"
            }
          }
        ]
      },
      {
        test : /\.gif/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : [
          {
            loader : "url-loader",
            options : {
              limit : 10000,
              mimetype : "image/gif"
            }
          }
        ]
      },
      {
        test : /\.jpg/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : [
          {
            loader : "url-loader",
            options : {
              limit : 10000,
              mimetype : "image/jpg"
            }
          }
        ]
      },
      {
        test : /\.png/,
        exclude : path.resolve(__dirname, "../node_modules"),
        use : [
          {
            loader : "url-loader",
            options : {
              // Package all files < 100kb into the JS package for ease of consumer
              limit : 100000,
              mimetype : "image/png",
              name : "[path][name].[ext]"
            }
          }
        ]
      },
      // ==========
      // = Styles =
      // ==========
      // Global CSS (from node_modules)
      // ==============================
      {
        test : /\.css/,
        use : [
          {
            loader : "style-loader"
          },
          {
            loader : 'css-loader'
          }
        ]
      },
      // "scss" loader
      {
        test : /\.scss$/,
        use : [
          "style-loader", // creates style nodes from JS strings
          "css-loader", // translates CSS into CommonJS
          "sass-loader" // compiles Sass to CSS
        ]
      },
    ]
  }

};
